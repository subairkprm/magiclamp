"""Tests for the LLM eval harness (brain/eval)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from brain.eval import (  # noqa: E402
    EvalCase,
    available_rules,
    load_cases,
    run,
    run_sync,
    score_output,
)


# ── Stub providers ──────────────────────────────────────────────────


class _EchoProvider:
    """Returns a deterministic response controlled by the test."""

    name = "echo"

    def __init__(self, response_for: dict[str, str] | None = None, default: str = ""):
        self._responses = response_for or {}
        self._default = default

    def model_name(self) -> str:
        return "echo-1"

    async def complete(self, prompt: str, system=None, json_mode: bool = False) -> str:
        return self._responses.get(prompt, self._default or prompt)


class _BoomProvider:
    name = "boom"

    def model_name(self) -> str:
        return "boom-1"

    async def complete(self, *a, **kw):
        raise RuntimeError("upstream blew up: super-secret-token-XYZ")


# ── Scoring rules ───────────────────────────────────────────────────


def test_available_rules_lists_all_supported_kinds():
    rules = available_rules()
    for r in ("contains", "not_contains", "regex", "max_length", "json_valid"):
        assert r in rules


def test_score_output_contains_is_case_insensitive_by_default():
    [res] = score_output([{"rule": "contains", "value": "AISHA"}], "hello aisha")
    assert res["passed"] is True


def test_score_output_contains_respects_case_sensitive():
    [res] = score_output(
        [{"rule": "contains", "value": "AISHA", "case_sensitive": True}],
        "hello aisha",
    )
    assert res["passed"] is False


def test_score_output_not_contains_inverts_contains():
    [res] = score_output([{"rule": "not_contains", "value": "secret"}], "hello world")
    assert res["passed"] is True


def test_score_output_regex_matches_arabic_block():
    # Any Arabic codepoint should match the unicode block range.
    [res] = score_output(
        [{"rule": "regex", "value": "[\\u0600-\\u06FF]"}],
        "حيّ العميلة عائشة",
    )
    assert res["passed"] is True


def test_score_output_max_length_enforced():
    [res] = score_output([{"rule": "max_length", "value": 5}], "hello world")
    assert res["passed"] is False
    assert res["actual"] == 11


def test_score_output_json_valid():
    [ok] = score_output([{"rule": "json_valid"}], '{"a": 1}')
    [bad] = score_output([{"rule": "json_valid"}], "not json")
    assert ok["passed"] is True
    assert bad["passed"] is False


# ── Loader ──────────────────────────────────────────────────────────


def test_load_cases_parses_smoke_set():
    path = Path(__file__).resolve().parent.parent / "brain" / "eval" / "cases" / "smoke.json"
    cases = load_cases(path)
    assert len(cases) >= 5
    ids = {c.id for c in cases}
    assert "en-greeting" in ids
    assert "ar-greeting" in ids


def test_load_cases_rejects_unknown_rule(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps([{"id": "x", "prompt": "hi", "rules": [{"rule": "nope"}]}])
    )
    with pytest.raises(ValueError, match="unknown rule"):
        load_cases(p)


def test_load_cases_rejects_duplicate_ids(tmp_path: Path):
    p = tmp_path / "dup.json"
    p.write_text(
        json.dumps(
            [
                {"id": "x", "prompt": "a"},
                {"id": "x", "prompt": "b"},
            ]
        )
    )
    with pytest.raises(ValueError, match="Duplicate"):
        load_cases(p)


def test_load_cases_rejects_missing_prompt(tmp_path: Path):
    p = tmp_path / "miss.json"
    p.write_text(json.dumps([{"id": "x"}]))
    with pytest.raises(ValueError, match="prompt"):
        load_cases(p)


# ── Runner ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_aggregates_pass_rate_correctly():
    cases = [
        EvalCase(
            id="pass-1",
            prompt="ping",
            rules=[{"rule": "contains", "value": "pong"}],
        ),
        EvalCase(
            id="fail-1",
            prompt="ping",
            rules=[{"rule": "contains", "value": "absent-string"}],
        ),
    ]
    provider = _EchoProvider(response_for={"ping": "pong"})
    report = await run(cases, provider)
    assert report.total == 2
    assert report.passed == 1
    assert report.failed == 1
    assert report.pass_rate == 0.5
    assert report.provider == "echo"
    assert report.model == "echo-1"
    # The per-case results carry the same provider/model + rule diagnostics.
    by_id = {c.id: c for c in report.cases}
    assert by_id["pass-1"].passed is True
    assert by_id["fail-1"].passed is False


@pytest.mark.asyncio
async def test_run_records_error_category_without_leaking_message():
    cases = [EvalCase(id="boom", prompt="x", rules=[])]
    report = await run(cases, _BoomProvider())
    [c] = report.cases
    assert c.passed is False
    assert c.error == "RuntimeError"
    # The runner must NOT echo the upstream exception text — it can carry
    # secrets (mirrors services.llm redaction).
    assert "super-secret-token-XYZ" not in c.output
    assert "super-secret-token-XYZ" not in (c.error or "")


@pytest.mark.asyncio
async def test_run_invokes_on_case_callback_for_each_case():
    cases = [
        EvalCase(id="a", prompt="x"),
        EvalCase(id="b", prompt="x"),
    ]
    seen: list[str] = []
    await run(cases, _EchoProvider(), on_case=lambda r: seen.append(r.id))
    assert seen == ["a", "b"]


def test_run_sync_returns_serialisable_report():
    cases = [EvalCase(id="ok", prompt="ping", rules=[])]
    report = run_sync(cases, _EchoProvider())
    # Must round-trip through json.dumps without help.
    payload = json.dumps(report.to_dict())
    again = json.loads(payload)
    assert again["total"] == 1
    assert again["passed"] == 1
    assert again["pass_rate"] == 1.0
    assert again["cases"][0]["id"] == "ok"


@pytest.mark.asyncio
async def test_smoke_eval_set_passes_against_a_perfect_stub():
    """Regression: the bundled smoke.json must be runnable end-to-end and
    achieve 100 % against a stub that returns ideal answers."""
    path = Path(__file__).resolve().parent.parent / "brain" / "eval" / "cases" / "smoke.json"
    cases = load_cases(path)

    # Map each case id → an ideal output that satisfies every rule.
    ideals = {
        "en-greeting": "Welcome back, Aisha.",
        "ar-greeting": "حيّاكِ الله يا عائشة.",
        "json-extract": '{"name": "Aisha", "city": "Dubai"}',
        "vat-knowledge": "The standard UAE VAT rate is 5 percent.",
        "no-pii-leak": "Customer called about a loan.",
    }
    by_id = {c.id: c for c in cases}
    response_for = {by_id[k].prompt: v for k, v in ideals.items()}

    report = await run(cases, _EchoProvider(response_for=response_for))
    assert report.passed == report.total, [
        (c.id, c.rule_results) for c in report.cases if not c.passed
    ]
