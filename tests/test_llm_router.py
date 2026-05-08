"""Tests for brain/core/llm_router.py — two-tier LLM routing."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import AsyncIterator, List, Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from core.llm_router import (  # noqa: E402
    DEFAULT_ESCALATE_SENTINEL,
    RouterDecision,
    RouterTier,
    TwoTierRouter,
    classify_complexity,
)


# ── Stub provider ───────────────────────────────────────────────────


class StubProvider:
    """Minimal LLMProvider stub — returns canned text and records calls."""

    def __init__(self, name: str, response: str, chunks: Optional[List[str]] = None):
        self.name = name
        self.response = response
        self.chunks = chunks or [response]
        self.calls: List[dict] = []

    async def complete(self, prompt, system=None, json_mode=False):
        self.calls.append(
            {"prompt": prompt, "system": system, "json_mode": json_mode}
        )
        return self.response

    async def stream(self, prompt, system=None) -> AsyncIterator[str]:
        self.calls.append({"prompt": prompt, "system": system, "stream": True})
        for c in self.chunks:
            yield c


def run(coro):
    # Use a fresh event loop per call so we don't depend on whatever
    # loop policy the surrounding test session left behind.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── classify_complexity ─────────────────────────────────────────────


class TestClassifyComplexity:
    def test_short_simple_prompt_is_fast(self):
        d = classify_complexity("What is the capital of UAE?")
        assert d.tier is RouterTier.FAST
        assert d.score == 0
        assert d.reasons == ()

    def test_multi_step_keyword_pushes_to_frontier(self):
        # Multi-step (2) + json_mode (2) = 4 → frontier.
        d = classify_complexity(
            "Compare and contrast Stripe vs Telr fees, step by step",
            json_mode=True,
        )
        assert d.tier is RouterTier.FRONTIER
        assert "multi_step_keyword" in d.reasons

    def test_arabic_multi_step_keyword_detected(self):
        d = classify_complexity("اشرح لي كيف يعمل الذكاء الاصطناعي")
        assert "multi_step_keyword" in d.reasons

    def test_json_mode_pushes_to_frontier(self):
        d = classify_complexity("Give me the user", json_mode=True)
        assert "json_mode" in d.reasons

    def test_code_block_pushes_to_frontier(self):
        # Code block (2) + multi-step "refactor" (2) = 4 → frontier.
        prompt = "Refactor this:\n```python\nprint(1)\n```"
        d = classify_complexity(prompt)
        assert d.tier is RouterTier.FRONTIER
        assert "code_block" in d.reasons
        assert "multi_step_keyword" in d.reasons

    def test_long_prompt_adds_weight(self):
        d = classify_complexity("hello " * 200)  # ~1200 chars
        assert "long_prompt" in d.reasons

    def test_very_long_prompt_adds_more(self):
        d = classify_complexity("hello " * 400)  # ~2400 chars
        assert "very_long_prompt" in d.reasons
        assert d.score >= 2

    def test_arabic_latin_code_switch_detected(self):
        d = classify_complexity("Send a WhatsApp إلى العميل now please")
        assert "arabic_latin_code_switch" in d.reasons

    def test_long_history_adds_weight(self):
        d = classify_complexity("ok", history_turns=10)
        assert "long_history" in d.reasons

    def test_threshold_can_be_lowered(self):
        # Just an Arabic+Latin mix scores 1; default threshold is 3 → fast.
        d = classify_complexity("Hello مرحبا")
        assert d.tier is RouterTier.FAST
        # With threshold=1 the same prompt now goes to frontier.
        d2 = classify_complexity("Hello مرحبا", threshold=1)
        assert d2.tier is RouterTier.FRONTIER

    def test_invalid_inputs_rejected(self):
        with pytest.raises(TypeError):
            classify_complexity(None)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            classify_complexity("x", history_turns=-1)
        with pytest.raises(ValueError):
            classify_complexity("x", threshold=0)


# ── TwoTierRouter ───────────────────────────────────────────────────


class TestTwoTierRouter:
    def test_simple_prompt_hits_fast_only(self):
        fast = StubProvider("fast", "Abu Dhabi")
        frontier = StubProvider("frontier", "should not be called")
        r = TwoTierRouter(fast, frontier)
        out = run(r.complete("What is the capital of UAE?"))
        assert out == "Abu Dhabi"
        assert len(fast.calls) == 1
        assert frontier.calls == []
        assert r.stats() == {"fast": 1, "frontier": 0, "escalated": 0}

    def test_complex_prompt_skips_fast(self):
        fast = StubProvider("fast", "should not be called")
        frontier = StubProvider("frontier", "long answer")
        r = TwoTierRouter(fast, frontier)
        out = run(
            r.complete("Compare and contrast step by step the two providers", json_mode=True)
        )
        assert out == "long answer"
        assert fast.calls == []
        assert len(frontier.calls) == 1
        assert r.stats() == {"fast": 0, "frontier": 1, "escalated": 0}

    def test_escalation_sentinel_triggers_frontier_retry(self):
        fast = StubProvider("fast", DEFAULT_ESCALATE_SENTINEL)
        frontier = StubProvider("frontier", "the real answer")
        r = TwoTierRouter(fast, frontier)
        out = run(r.complete("a short prompt"))
        assert out == "the real answer"
        assert len(fast.calls) == 1
        assert len(frontier.calls) == 1
        assert r.stats() == {"fast": 0, "frontier": 1, "escalated": 1}

    def test_escalation_is_case_and_whitespace_insensitive(self):
        fast = StubProvider("fast", "  escalate\n")
        frontier = StubProvider("frontier", "ok")
        r = TwoTierRouter(fast, frontier)
        assert run(r.complete("short")) == "ok"
        assert r.stats()["escalated"] == 1

    def test_custom_sentinel_respected(self):
        fast = StubProvider("fast", "PASS")
        frontier = StubProvider("frontier", "boom")
        r = TwoTierRouter(fast, frontier, escalate_sentinel="pass")
        assert run(r.complete("hi")) == "boom"
        assert r.stats()["escalated"] == 1

    def test_streaming_dispatches_to_picked_tier(self):
        fast = StubProvider("fast", "a", chunks=["a", "b"])
        frontier = StubProvider("frontier", "x", chunks=["x", "y", "z"])
        r = TwoTierRouter(fast, frontier)

        async def collect(prompt, **kw):
            return [c async for c in r.stream(prompt, **kw)]

        # Simple prompt → fast.
        assert run(collect("hi")) == ["a", "b"]
        # Complex prompt → frontier.
        assert run(collect("Refactor this:\n```py\nprint()\n```")) == ["x", "y", "z"]
        assert r.stats()["fast"] >= 1
        assert r.stats()["frontier"] >= 1

    def test_streaming_does_not_escalate(self):
        # Even if the fast stream emits the sentinel, streaming is one-shot.
        fast = StubProvider("fast", DEFAULT_ESCALATE_SENTINEL,
                            chunks=[DEFAULT_ESCALATE_SENTINEL])
        frontier = StubProvider("frontier", "x", chunks=["x"])
        r = TwoTierRouter(fast, frontier)

        async def collect():
            return [c async for c in r.stream("hi")]

        assert run(collect()) == [DEFAULT_ESCALATE_SENTINEL]
        assert r.stats()["escalated"] == 0

    def test_reset_stats_clears_counters(self):
        fast = StubProvider("fast", "ok")
        frontier = StubProvider("frontier", "ok")
        r = TwoTierRouter(fast, frontier)
        run(r.complete("hi"))
        assert r.stats()["fast"] == 1
        r.reset_stats()
        assert r.stats() == {"fast": 0, "frontier": 0, "escalated": 0}

    def test_stats_returns_a_copy(self):
        r = TwoTierRouter(StubProvider("a", "x"), StubProvider("b", "y"))
        s = r.stats()
        s["fast"] = 999
        assert r.stats()["fast"] == 0

    def test_threshold_propagates_to_decide(self):
        fast = StubProvider("fast", "f")
        frontier = StubProvider("frontier", "F")
        r = TwoTierRouter(fast, frontier, threshold=1)
        # An Arabic+Latin mix scores 1 — at threshold=1 it should be FRONTIER.
        d = r.decide("Hello مرحبا")
        assert d.tier is RouterTier.FRONTIER

    def test_construction_validation(self):
        good = StubProvider("g", "x")
        with pytest.raises(ValueError, match="required"):
            TwoTierRouter(None, good)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="required"):
            TwoTierRouter(good, None)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="threshold"):
            TwoTierRouter(good, good, threshold=0)
        with pytest.raises(ValueError, match="escalate_sentinel"):
            TwoTierRouter(good, good, escalate_sentinel="   ")

    def test_decision_dataclass_is_frozen(self):
        d = RouterDecision(tier=RouterTier.FAST, score=0, reasons=())
        with pytest.raises(Exception):
            d.score = 99  # type: ignore[misc]
