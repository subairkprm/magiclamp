"""Tests for the UAE locale helpers (AED currency, VAT)."""

from __future__ import annotations

import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from core.locale import (  # noqa: E402
    VAT_RATE_UAE,
    VATBreakdown,
    compute_vat,
    format_aed,
)


def test_vat_rate_constant_matches_fta():
    # UAE Federal Tax Authority — standard rate is 5 %.
    assert VAT_RATE_UAE == Decimal("0.05")


def test_compute_vat_basic_round_number():
    b = compute_vat("100")
    assert b == VATBreakdown(
        net=Decimal("100.00"),
        vat=Decimal("5.00"),
        gross=Decimal("105.00"),
        rate=Decimal("0.05"),
    )


def test_compute_vat_invariant_holds_after_rounding():
    # An awkward fraction should still keep net + vat == gross post-rounding.
    b = compute_vat("33.33")
    assert b.net + b.vat == b.gross
    # 5% of 33.33 = 1.6665 -> rounds half-up to 1.67, gross = 35.00
    assert b.vat == Decimal("1.67")
    assert b.gross == Decimal("35.00")


def test_compute_vat_accepts_floats_without_binary_drift():
    b = compute_vat(0.1 + 0.2)  # this is 0.30000000000000004 as a float
    assert b.net == Decimal("0.30")
    assert b.vat == Decimal("0.02")  # 0.015 -> half-up to 0.02
    assert b.gross == Decimal("0.32")


def test_compute_vat_rejects_negative_amount():
    with pytest.raises(ValueError):
        compute_vat(-1)


def test_format_aed_default_western_digits():
    assert format_aed(1234.5) == "AED 1,234.50"
    assert format_aed(0) == "AED 0.00"
    assert format_aed("999999.999") == "AED 1,000,000.00"  # round half-up


def test_format_aed_arabic_indic_digits_and_separators():
    out = format_aed(99, arabic_indic_digits=True)
    # Western digits must not appear in the numeric portion.
    assert "9" not in out.split(" ", 1)[1]
    assert out.startswith("AED ")
    # Arabic decimal separator U+066B must be used in place of '.'.
    assert "\u066b" in out
    assert "." not in out


def test_format_aed_thousands_separator_in_arabic_indic_mode():
    out = format_aed(1234567, arabic_indic_digits=True)
    assert "," not in out
    assert "\u066c" in out  # Arabic thousands separator
