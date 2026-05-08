"""LLM eval harness — minimal, dependency-free, pluggable.

This is the QA + AI/LLM agents' shared test bed for catching prompt
regressions release-over-release. It deliberately stays small and uses only
what's already in the repo (the pluggable provider Protocol from ADR 0005,
stdlib `json`, `asyncio`, `dataclasses`).

A *case* is one row of the eval set: a prompt, an optional system message,
and a list of scoring rules. A *runner* asks one provider to answer every
case, scores each result, and produces a JSON report that can be diffed
between releases or pinned in CI as a quality gate (see ROADMAP.md → Phase 0
"Eval harness scaffolding").

Why we *don't* call the live LLM in unit tests: the harness is exercised in
CI by injecting a fake provider that satisfies the same `LLMProvider`
protocol (see `tests/test_eval_harness.py`). The real-provider runs are
opt-in via the `lamp-eval` CLI added below.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

# ── Scoring rules ───────────────────────────────────────────────────
#
# Each rule is a small JSON-serialisable spec. The runner evaluates them in
# order and the case passes only if *every* rule passes. Keeping the rule
# vocabulary tiny is on purpose: it makes the eval set human-readable and
# lets the QA agent author cases without writing Python.

_RuleResult = Dict[str, Any]


def _score_contains(rule: Dict[str, Any], output: str) -> _RuleResult:
    needle = rule["value"]
    case_sensitive = bool(rule.get("case_sensitive", False))
    haystack = output if case_sensitive else output.lower()
    needle_cmp = needle if case_sensitive else needle.lower()
    passed = needle_cmp in haystack
    return {"rule": "contains", "value": needle, "passed": passed}


def _score_not_contains(rule: Dict[str, Any], output: str) -> _RuleResult:
    res = _score_contains(rule, output)
    res["rule"] = "not_contains"
    res["passed"] = not res["passed"]
    return res


def _score_regex(rule: Dict[str, Any], output: str) -> _RuleResult:
    pattern = rule["value"]
    flags = re.IGNORECASE if rule.get("case_sensitive") is False else 0
    passed = re.search(pattern, output, flags) is not None
    return {"rule": "regex", "value": pattern, "passed": passed}


def _score_max_length(rule: Dict[str, Any], output: str) -> _RuleResult:
    limit = int(rule["value"])
    return {
        "rule": "max_length",
        "value": limit,
        "actual": len(output),
        "passed": len(output) <= limit,
    }


def _score_json_valid(rule: Dict[str, Any], output: str) -> _RuleResult:
    try:
        json.loads(output)
        passed = True
    except (ValueError, TypeError):
        passed = False
    return {"rule": "json_valid", "passed": passed}


_SCORERS: Dict[str, Callable[[Dict[str, Any], str], _RuleResult]] = {
    "contains": _score_contains,
    "not_contains": _score_not_contains,
    "regex": _score_regex,
    "max_length": _score_max_length,
    "json_valid": _score_json_valid,
}


def available_rules() -> List[str]:
    """Return the list of supported scoring-rule names (for docs / CLI help)."""
    return sorted(_SCORERS.keys())


# ── Case + report data classes ──────────────────────────────────────


@dataclass
class EvalCase:
    """One row of an eval set."""

    id: str
    prompt: str
    system: Optional[str] = None
    rules: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class CaseResult:
    """Outcome of running a single case against one provider."""

    id: str
    provider: str
    model: str
    output: str
    rule_results: List[_RuleResult]
    passed: bool
    duration_ms: int
    tags: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class EvalReport:
    """Aggregate report for one full eval run."""

    provider: str
    model: str
    started_at: float
    duration_ms: int
    total: int
    passed: int
    failed: int
    pass_rate: float
    cases: List[CaseResult]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Loading + running ───────────────────────────────────────────────


def load_cases(path: str | Path) -> List[EvalCase]:
    """Load a JSON eval set from disk.

    Format: a top-level list of ``{id, prompt, system?, rules?, tags?}`` objects.
    Unknown fields are ignored to keep the file forwards-compatible.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Eval set root must be a JSON array of cases")
    cases: List[EvalCase] = []
    seen_ids: set[str] = set()
    for raw in data:
        if not isinstance(raw, dict):
            raise ValueError("Each case must be a JSON object")
        cid = raw.get("id")
        if not cid or not isinstance(cid, str):
            raise ValueError("Each case must have a non-empty string `id`")
        if cid in seen_ids:
            raise ValueError(f"Duplicate case id: {cid!r}")
        seen_ids.add(cid)
        if "prompt" not in raw or not isinstance(raw["prompt"], str):
            raise ValueError(f"Case {cid!r}: missing or non-string `prompt`")
        rules = raw.get("rules", []) or []
        for r in rules:
            if r.get("rule") not in _SCORERS:
                raise ValueError(
                    f"Case {cid!r}: unknown rule {r.get('rule')!r}; "
                    f"known rules: {available_rules()}"
                )
        cases.append(
            EvalCase(
                id=cid,
                prompt=raw["prompt"],
                system=raw.get("system"),
                rules=rules,
                tags=list(raw.get("tags") or []),
            )
        )
    return cases


def score_output(rules: Sequence[Dict[str, Any]], output: str) -> List[_RuleResult]:
    """Apply ``rules`` to ``output`` in order and return the per-rule results."""
    return [_SCORERS[r["rule"]](r, output) for r in rules]


# Type alias for "anything that quacks like an LLMProvider" — we deliberately
# don't import core.llm.LLMProvider here so the harness can be used as a
# library without dragging the rest of the brain in.
ProviderLike = Any


async def run(
    cases: Sequence[EvalCase],
    provider: ProviderLike,
    *,
    on_case: Optional[Callable[[CaseResult], None]] = None,
) -> EvalReport:
    """Run every ``case`` against ``provider`` and return an :class:`EvalReport`.

    ``provider`` only needs ``.name`` (str), ``.model_name() -> str`` and
    ``async complete(prompt, system=None, json_mode=False) -> str``. This is
    deliberately the same shape as the LLMProvider Protocol in
    ``brain/core/llm/__init__.py`` so any registered adapter Just Works.
    """
    name = getattr(provider, "name", "unknown")
    model = provider.model_name() if hasattr(provider, "model_name") else "unknown"

    started = time.time()
    started_perf = time.perf_counter()
    results: List[CaseResult] = []

    for case in cases:
        t0 = time.perf_counter()
        error: Optional[str] = None
        output = ""
        try:
            output = await provider.complete(prompt=case.prompt, system=case.system)
        except Exception as e:  # noqa: BLE001 — harness must isolate cases
            # Keep error category, never the message — it can echo upstream
            # secrets (mirrors the redaction in services.llm).
            error = type(e).__name__

        duration_ms = int((time.perf_counter() - t0) * 1000)
        rule_results = score_output(case.rules, output) if error is None else []
        passed = error is None and all(r["passed"] for r in rule_results)

        cr = CaseResult(
            id=case.id,
            provider=name,
            model=model,
            output=output,
            rule_results=rule_results,
            passed=passed,
            duration_ms=duration_ms,
            tags=list(case.tags),
            error=error,
        )
        results.append(cr)
        if on_case is not None:
            on_case(cr)

    duration_ms = int((time.perf_counter() - started_perf) * 1000)
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    return EvalReport(
        provider=name,
        model=model,
        started_at=started,
        duration_ms=duration_ms,
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=(passed / total) if total else 1.0,
        cases=results,
    )


def run_sync(cases: Sequence[EvalCase], provider: ProviderLike) -> EvalReport:
    """Convenience wrapper for sync callers (CLI, scripts)."""
    return asyncio.run(run(cases, provider))


__all__ = [
    "EvalCase",
    "CaseResult",
    "EvalReport",
    "available_rules",
    "load_cases",
    "score_output",
    "run",
    "run_sync",
]
