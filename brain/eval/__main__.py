"""``python -m brain.eval`` — run an eval set against a configured provider.

Usage:
    python -m brain.eval --cases brain/eval/cases/smoke.json
    python -m brain.eval --cases brain/eval/cases/smoke.json --provider jais
    python -m brain.eval --cases brain/eval/cases/smoke.json --json out.json --min-pass-rate 0.95

Exits non-zero when ``pass_rate < --min-pass-rate``, so this can be wired
straight into CI as a release quality gate (see ROADMAP.md → quality gates).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import load_cases, run_sync


def _add_brain_to_path() -> None:
    # Allow ``python -m brain.eval`` from a checkout where the ``brain``
    # package isn't on sys.path yet (mirrors the test setUp).
    here = Path(__file__).resolve().parent.parent  # .../brain
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lamp-eval", description=__doc__)
    parser.add_argument("--cases", required=True, help="Path to JSON eval set")
    parser.add_argument(
        "--provider",
        default=None,
        help="LLM provider name (defaults to LLM_PROVIDER env / openai)",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        default=None,
        help="Write the full JSON report to this path",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.0,
        help="Exit non-zero if pass_rate is below this threshold (0.0–1.0)",
    )
    args = parser.parse_args(argv)

    _add_brain_to_path()
    from core.llm import get_provider  # noqa: E402  (import after path setup)

    cases = load_cases(args.cases)
    provider = get_provider(args.provider)
    report = run_sync(cases, provider)

    # Always emit a one-line human summary on stderr so logs are readable.
    print(
        f"[{report.provider}/{report.model}] {report.passed}/{report.total} "
        f"passed ({report.pass_rate:.0%}) in {report.duration_ms} ms",
        file=sys.stderr,
    )
    for c in report.cases:
        if not c.passed:
            failures = [r for r in c.rule_results if not r.get("passed")]
            print(f"  ✗ {c.id}: {c.error or failures}", file=sys.stderr)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if report.pass_rate < args.min_pass_rate:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
