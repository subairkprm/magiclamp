"""Tests for brain/core/uae_id.py — Emirates ID + UAE mobile helpers."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from core.uae_id import (  # noqa: E402
    format_emirates_id,
    is_valid_emirates_id,
    is_valid_uae_mobile,
    normalize_uae_mobile,
)


# Computed Luhn-valid samples (see header script in PR description).
VALID_EID_1 = "784198512345673"  # 1985 birth-year, valid Luhn checksum
VALID_EID_2 = "784200198765438"  # 2001 birth-year, valid Luhn checksum


# ── Emirates ID ─────────────────────────────────────────────────────


class TestIsValidEmiratesId:
    def test_accepts_canonical_dashed_form(self):
        assert is_valid_emirates_id("784-1985-1234567-3") is True

    def test_accepts_undashed_form(self):
        assert is_valid_emirates_id(VALID_EID_1) is True
        assert is_valid_emirates_id(VALID_EID_2) is True

    def test_accepts_mixed_separators(self):
        assert is_valid_emirates_id("784 1985 1234567 3") is True
        assert is_valid_emirates_id("784/1985/1234567/3") is True

    def test_rejects_wrong_country_prefix(self):
        # Same Luhn-valid digits but starting with 783 instead of 784.
        assert is_valid_emirates_id("783-1985-1234567-3") is False

    def test_rejects_wrong_length(self):
        assert is_valid_emirates_id("78419851234567") is False  # 14
        assert is_valid_emirates_id(VALID_EID_1 + "0") is False  # 16

    def test_rejects_bad_checksum(self):
        assert is_valid_emirates_id("784198512345670") is False  # last digit off
        assert is_valid_emirates_id("784198512345679") is False  # also bad

    def test_rejects_implausible_birth_year(self):
        # 0000 birth-year — Luhn would pass on some combos but the year is junk.
        assert is_valid_emirates_id("784-0000-0000000-0") is False

    def test_rejects_non_strings(self):
        assert is_valid_emirates_id(None) is False  # type: ignore[arg-type]
        assert is_valid_emirates_id(784198512345673) is False  # type: ignore[arg-type]


class TestFormatEmiratesId:
    def test_renders_canonical_dashed_form(self):
        assert format_emirates_id(VALID_EID_1) == "784-1985-1234567-3"
        assert format_emirates_id("784 1985 1234567 3") == "784-1985-1234567-3"

    def test_raises_on_invalid(self):
        with pytest.raises(ValueError, match="Invalid Emirates ID"):
            format_emirates_id("784-0000-0000000-0")


# ── UAE mobile ──────────────────────────────────────────────────────


class TestNormalizeUaeMobile:
    @pytest.mark.parametrize(
        "raw",
        [
            "+971501234567",
            "+971 50 123 4567",
            "+971-50-123-4567",
            "00971501234567",
            "971501234567",
            "0501234567",
            "501234567",
            "(+971) 50 123 4567",
        ],
    )
    def test_canonicalises_to_e164(self, raw):
        assert normalize_uae_mobile(raw) == "+971501234567"

    @pytest.mark.parametrize("prefix", ["50", "52", "54", "55", "56", "58"])
    def test_accepts_every_allocated_mobile_prefix(self, prefix):
        assert normalize_uae_mobile(f"0{prefix}1234567") == f"+971{prefix}1234567"

    @pytest.mark.parametrize("prefix", ["51", "53", "57", "59"])
    def test_rejects_unallocated_mobile_prefix(self, prefix):
        with pytest.raises(ValueError, match="not an allocated mobile prefix"):
            normalize_uae_mobile(f"0{prefix}1234567")

    def test_rejects_landline(self):
        # 04 is Dubai landline — must not be treated as mobile.
        with pytest.raises(ValueError, match="UAE mobile"):
            normalize_uae_mobile("+97143434343")

    def test_rejects_wrong_length(self):
        with pytest.raises(ValueError):
            normalize_uae_mobile("+97150123")

    def test_rejects_non_string(self):
        with pytest.raises(TypeError):
            normalize_uae_mobile(971501234567)  # type: ignore[arg-type]


class TestIsValidUaeMobile:
    def test_true_for_canonical(self):
        assert is_valid_uae_mobile("+971501234567") is True

    def test_false_for_garbage(self):
        assert is_valid_uae_mobile("not-a-number") is False
        assert is_valid_uae_mobile("") is False
        assert is_valid_uae_mobile(None) is False  # type: ignore[arg-type]
