"""Two-tier LLM router — cheap "fast" tier + capable "frontier" tier.

The product needs sub-second first-token latency on the easy 80% of
prompts (lookups, short answers, autocompletes) but cannot regress on
the hard 20% (multi-step reasoning, code generation, structured JSON,
Arabic ⇄ English code-switching). Sending everything to the frontier
model burns budget; sending everything to the cheap one drops quality.

This module is the *routing brain*:

* It owns the heuristic that decides which tier handles a prompt.
* It dispatches to two pluggable :class:`LLMProvider` instances that the
  caller wires in. The router itself does no I/O and pulls in no SDKs,
  so it's trivially unit-testable with stub providers (mirroring the
  eval-harness pattern in ``brain/eval``).
* It supports an *escalation* protocol: a router-style fast model can be
  prompted to answer or emit a sentinel like ``"ESCALATE"`` when it's
  unsure; the router will then re-issue the same prompt to the frontier
  tier. This is the standard "router LLM + synthesiser LLM" pattern.
* It exposes per-tier counters so the dashboard can plot the fast/
  frontier/escalation mix over time without a separate metrics layer.

The classifier is deliberately *cheap heuristics*, not an LLM call —
otherwise we'd pay frontier cost just to decide whether to pay frontier
cost. Tests pin the contract; tweak the weights when real traffic
disagrees.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Dict, Optional, Protocol, runtime_checkable


# ── Provider contract (re-stated locally for typing without an import cycle) ─


@runtime_checkable
class LLMProvider(Protocol):
    """Subset of :class:`brain.core.llm.LLMProvider` we actually use here.

    Re-declared as a local Protocol so this module has zero hard imports
    from ``brain.core.llm`` — that keeps unit tests fast (no provider
    SDKs loaded) and avoids circular imports if the router itself is
    later registered as a meta-provider.
    """

    name: str

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str: ...

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> AsyncIterator[str]: ...


# ── Tiers + decisions ───────────────────────────────────────────────


class RouterTier(str, Enum):
    """Which provider tier handled (or should handle) a request."""

    FAST = "fast"
    FRONTIER = "frontier"


@dataclass(frozen=True)
class RouterDecision:
    """The classifier's verdict for one prompt.

    ``score`` is the raw complexity score (higher = more complex). It's
    surfaced so callers can log it / build histograms; the actual tier
    pick uses the threshold inside :class:`TwoTierRouter`.
    """

    tier: RouterTier
    score: int
    reasons: tuple = field(default_factory=tuple)


# ── Heuristic classifier ────────────────────────────────────────────

# Lowercased substrings that suggest multi-step reasoning. Order doesn't
# matter — any match contributes the same weight.
_MULTI_STEP_KEYWORDS = (
    "step by step",
    "step-by-step",
    "explain why",
    "compare and contrast",
    "pros and cons",
    "trade-off",
    "tradeoff",
    "derive",
    "prove that",
    "summarise the differences",
    "summarize the differences",
    "analyse",
    "analyze",
    "plan ",  # "plan a launch" / "plan the migration"
    "design a",
    "architect",
    "refactor",
    "translate the following",
    # Arabic equivalents — the product is bilingual.
    "اشرح",        # explain
    "قارن",        # compare
    "حلل",         # analyse
    "صمم",         # design
    "خطوة بخطوة",  # step by step
)

_CODE_FENCE_RE = re.compile(r"```")
# Detect Arabic-script characters (basic + supplement + presentation forms).
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
# Detect Latin-script word characters.
_LATIN_RE = re.compile(r"[A-Za-z]")

# Score thresholds — keep as named constants so they're tweakable without
# hunting through the function body.
_LONG_PROMPT_CHARS = 800       # raw length above which we add weight
_VERY_LONG_PROMPT_CHARS = 2000  # one extra weight bump beyond this
_LONG_HISTORY_TURNS = 6         # multi-turn conversations get harder fast
_DEFAULT_FRONTIER_THRESHOLD = 3  # decision score >= this → frontier


def classify_complexity(
    prompt: str,
    *,
    json_mode: bool = False,
    history_turns: int = 0,
    threshold: int = _DEFAULT_FRONTIER_THRESHOLD,
) -> RouterDecision:
    """Decide which tier should handle ``prompt``.

    Pure heuristic — no I/O, no LLM call. Returns a
    :class:`RouterDecision` carrying the chosen tier, the raw score, and
    the human-readable reasons that pushed it over (useful for logs and
    dashboards).

    Parameters
    ----------
    prompt : str
        The user's prompt text.
    json_mode : bool
        If True the caller is asking for structured output; that
        consistently does better on frontier models, so weight it.
    history_turns : int
        How many prior conversation turns are being replayed. Long
        threads are correlated with harder synthesis tasks.
    threshold : int
        Minimum score that selects ``FRONTIER``. Default 3; lower it
        to bias towards quality, raise it to bias towards cost.
    """
    if not isinstance(prompt, str):
        raise TypeError(f"prompt must be str, got {type(prompt).__name__}")
    if history_turns < 0:
        raise ValueError(f"history_turns must be >= 0, got {history_turns}")
    if threshold < 1:
        raise ValueError(f"threshold must be >= 1, got {threshold}")

    score = 0
    reasons = []
    text = prompt.strip()
    lowered = text.lower()

    # 1) Length.
    n = len(text)
    if n >= _VERY_LONG_PROMPT_CHARS:
        score += 2
        reasons.append("very_long_prompt")
    elif n >= _LONG_PROMPT_CHARS:
        score += 1
        reasons.append("long_prompt")

    # 2) Multi-step / reasoning cue words.
    if any(kw in lowered for kw in _MULTI_STEP_KEYWORDS):
        score += 2
        reasons.append("multi_step_keyword")

    # 3) Structured-output requests need stronger models for reliability.
    if json_mode:
        score += 2
        reasons.append("json_mode")

    # 4) Code blocks (review / debug / generate code).
    if _CODE_FENCE_RE.search(text):
        score += 2
        reasons.append("code_block")

    # 5) Bilingual code-switching: both Arabic and Latin in the same prompt.
    has_arabic = bool(_ARABIC_RE.search(text))
    has_latin = bool(_LATIN_RE.search(text))
    if has_arabic and has_latin:
        score += 1
        reasons.append("arabic_latin_code_switch")

    # 6) Long conversation context.
    if history_turns >= _LONG_HISTORY_TURNS:
        score += 1
        reasons.append("long_history")

    tier = RouterTier.FRONTIER if score >= threshold else RouterTier.FAST
    return RouterDecision(tier=tier, score=score, reasons=tuple(reasons))


# ── Router itself ───────────────────────────────────────────────────


# Sentinel a router-style "fast" model can emit to ask for an escalation.
# Compared case-insensitively after stripping whitespace.
DEFAULT_ESCALATE_SENTINEL = "ESCALATE"


class TwoTierRouter:
    """Dispatches prompts to a fast or frontier provider.

    The router owns no provider state itself — the caller wires in two
    objects that satisfy :class:`LLMProvider`. This makes the router
    trivially testable with stubs and lets ops swap either tier
    independently (e.g. Groq for fast, Anthropic for frontier).

    Counters are exposed via :meth:`stats` so the admin dashboard can
    render the fast/frontier/escalation split without reaching into
    private state.
    """

    def __init__(
        self,
        fast: LLMProvider,
        frontier: LLMProvider,
        *,
        threshold: int = _DEFAULT_FRONTIER_THRESHOLD,
        escalate_sentinel: str = DEFAULT_ESCALATE_SENTINEL,
    ) -> None:
        if fast is None or frontier is None:
            raise ValueError("Both fast and frontier providers are required")
        if threshold < 1:
            raise ValueError(f"threshold must be >= 1, got {threshold}")
        # An empty / whitespace-only sentinel would match every fast
        # response and trigger an escalation storm.
        if not escalate_sentinel or not escalate_sentinel.strip():
            raise ValueError("escalate_sentinel must be a non-empty string")
        self.fast = fast
        self.frontier = frontier
        self.threshold = threshold
        self.escalate_sentinel = escalate_sentinel.strip().upper()
        self._counters: Dict[str, int] = {
            "fast": 0,
            "frontier": 0,
            "escalated": 0,
        }

    # ── Public API ─────────────────────────────────────────────────

    def decide(
        self,
        prompt: str,
        *,
        json_mode: bool = False,
        history_turns: int = 0,
    ) -> RouterDecision:
        """Public wrapper around :func:`classify_complexity` using our threshold."""
        return classify_complexity(
            prompt,
            json_mode=json_mode,
            history_turns=history_turns,
            threshold=self.threshold,
        )

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        *,
        json_mode: bool = False,
        history_turns: int = 0,
    ) -> str:
        """Route ``prompt`` to the appropriate tier and return the answer.

        If the fast tier responds with the escalation sentinel (after
        stripping + case-folding), the prompt is re-issued to the
        frontier tier and the escalation counter is bumped.
        """
        decision = self.decide(
            prompt, json_mode=json_mode, history_turns=history_turns
        )
        if decision.tier is RouterTier.FRONTIER:
            self._counters["frontier"] += 1
            return await self.frontier.complete(prompt, system=system, json_mode=json_mode)

        # Fast tier handles it first.
        result = await self.fast.complete(prompt, system=system, json_mode=json_mode)
        if self._is_escalation(result):
            self._counters["escalated"] += 1
            self._counters["frontier"] += 1
            return await self.frontier.complete(prompt, system=system, json_mode=json_mode)
        self._counters["fast"] += 1
        return result

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        *,
        json_mode: bool = False,
        history_turns: int = 0,
    ) -> AsyncIterator[str]:
        """Stream tokens from the picked tier.

        Streaming intentionally does *not* implement the escalation
        retry — once we've started flushing tokens to the client we
        can't take them back. Callers that need escalation should use
        :meth:`complete` instead.
        """
        decision = self.decide(
            prompt, json_mode=json_mode, history_turns=history_turns
        )
        if decision.tier is RouterTier.FRONTIER:
            self._counters["frontier"] += 1
            provider = self.frontier
        else:
            self._counters["fast"] += 1
            provider = self.fast
        async for chunk in provider.stream(prompt, system=system):
            yield chunk

    def stats(self) -> Dict[str, int]:
        """Snapshot of the per-tier + escalation counters.

        Returned as a copy so callers can't mutate the router's state.
        """
        return dict(self._counters)

    def reset_stats(self) -> None:
        """Zero the counters — useful between dashboard sampling windows."""
        for k in self._counters:
            self._counters[k] = 0

    # ── Internal helpers ───────────────────────────────────────────

    def _is_escalation(self, response: str) -> bool:
        if not isinstance(response, str):
            return False
        return response.strip().upper() == self.escalate_sentinel


__all__ = [
    "LLMProvider",
    "RouterTier",
    "RouterDecision",
    "TwoTierRouter",
    "classify_complexity",
    "DEFAULT_ESCALATE_SENTINEL",
]
