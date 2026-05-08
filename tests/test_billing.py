"""Tests for the billing pipeline scaffold (brain/core/billing.py)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from core.billing import (  # noqa: E402
    BillingProvider,
    Invoice,
    InvoiceLine,
    build_invoice,
    to_provider_payload,
)
from core.locale import VAT_RATE_UAE, format_aed  # noqa: E402


# ── BillingProvider parsing ─────────────────────────────────────────


class TestBillingProviderParse:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("stripe", BillingProvider.STRIPE),
            ("Stripe", BillingProvider.STRIPE),
            ("  TELR ", BillingProvider.TELR),
            ("tabby", BillingProvider.TABBY),
        ],
    )
    def test_parse_accepts_case_insensitive_strings(self, raw, expected):
        assert BillingProvider.parse(raw) is expected

    @pytest.mark.parametrize("bad", ["", "paypal", None, 1])
    def test_parse_rejects_unknown(self, bad):
        with pytest.raises(ValueError):
            BillingProvider.parse(bad)


# ── InvoiceLine validation ──────────────────────────────────────────


class TestInvoiceLine:
    def test_line_total_is_quantity_times_unit_price(self):
        line = InvoiceLine(description="Pro seat", quantity=3, unit_price_aed=Decimal("99"))
        assert line.line_total_aed == Decimal("297")

    def test_unit_price_coerces_int_float_str(self):
        for raw in (99, 99.0, "99"):
            line = InvoiceLine(description="seat", quantity=1, unit_price_aed=raw)
            assert line.unit_price_aed == Decimal("99")

    def test_rejects_empty_description(self):
        with pytest.raises(ValueError, match="description"):
            InvoiceLine(description="   ", quantity=1, unit_price_aed=10)

    def test_rejects_non_positive_quantity(self):
        for q in (0, -1):
            with pytest.raises(ValueError, match="quantity"):
                InvoiceLine(description="seat", quantity=q, unit_price_aed=10)

    def test_rejects_negative_unit_price(self):
        with pytest.raises(ValueError, match="unit_price"):
            InvoiceLine(description="seat", quantity=1, unit_price_aed=-1)


# ── Invoice totals + invariants ─────────────────────────────────────


class TestInvoice:
    def _line(self, qty=1, price="100"):
        return InvoiceLine(description="Pro seat", quantity=qty, unit_price_aed=price)

    def test_single_line_totals_use_uae_5pct_vat(self):
        inv = build_invoice(
            invoice_number="INV-001",
            workspace_id="ws-1",
            customer_name="Aisha LLC",
            lines=[self._line(qty=1, price="100")],
            provider="stripe",
        )
        assert inv.net_total_aed == Decimal("100.00")
        assert inv.vat_total_aed == Decimal("5.00")
        assert inv.gross_total_aed == Decimal("105.00")
        assert inv.vat_rate == VAT_RATE_UAE

    def test_multi_line_totals_sum_correctly(self):
        inv = build_invoice(
            invoice_number="INV-002",
            workspace_id="ws-1",
            customer_name="Aisha LLC",
            lines=[
                InvoiceLine(description="Pro seat", quantity=3, unit_price_aed="99"),
                InvoiceLine(description="Add-on", quantity=2, unit_price_aed="50"),
            ],
            provider="telr",
        )
        # 3*99 + 2*50 = 297 + 100 = 397 net; vat = 19.85; gross = 416.85
        assert inv.net_total_aed == Decimal("397.00")
        assert inv.vat_total_aed == Decimal("19.85")
        assert inv.gross_total_aed == Decimal("416.85")
        # Invariant: net + vat == gross.
        assert inv.net_total_aed + inv.vat_total_aed == inv.gross_total_aed

    def test_rejects_empty_lines(self):
        with pytest.raises(ValueError, match="at least one line"):
            Invoice(
                invoice_number="X",
                workspace_id="ws",
                customer_name="C",
                lines=[],
                provider=BillingProvider.STRIPE,
            )

    def test_rejects_non_aed_currency(self):
        with pytest.raises(ValueError, match="AED"):
            Invoice(
                invoice_number="X",
                workspace_id="ws",
                customer_name="C",
                lines=[self._line()],
                provider=BillingProvider.STRIPE,
                currency="USD",
            )


# ── Provider payload rendering ──────────────────────────────────────


class TestToProviderPayload:
    def _inv(self, provider="stripe"):
        return build_invoice(
            invoice_number="INV-100",
            workspace_id="ws-42",
            customer_name="Aisha Holdings LLC",
            lines=[
                InvoiceLine(description="Pro seat", quantity=2, unit_price_aed="150.00"),
            ],
            provider=provider,
            seller_trn="100123456700003",
            customer_trn="100987654300003",
            due_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            notes="Thanks for your business",
        )

    def test_payload_is_json_serialisable(self):
        payload = to_provider_payload(self._inv())
        # Round-trip through json.dumps without help — confirms there are
        # no Decimal/datetime leftovers any provider SDK would choke on.
        again = json.loads(json.dumps(payload))
        assert again["invoice_number"] == "INV-100"

    def test_payload_money_fields_are_integer_fils(self):
        payload = to_provider_payload(self._inv())
        # 2 * 150 AED = 300 AED net -> 30000 fils
        # 5% VAT = 15 AED -> 1500 fils
        # Gross = 315 AED -> 31500 fils
        assert payload["totals"]["net_fils"] == 30000
        assert payload["totals"]["vat_fils"] == 1500
        assert payload["totals"]["gross_fils"] == 31500
        assert payload["lines"][0]["unit_price_fils"] == 15000
        assert payload["lines"][0]["line_total_fils"] == 30000
        # All money fields must be ints (not floats) — minor-units only.
        for key in ("net_fils", "vat_fils", "gross_fils"):
            assert isinstance(payload["totals"][key], int)

    def test_payload_uses_format_aed_for_display_strings(self):
        payload = to_provider_payload(self._inv())
        assert payload["totals"]["gross_display"] == format_aed(Decimal("315.00"))
        assert payload["totals"]["net_display"] == format_aed(Decimal("300.00"))
        assert payload["totals"]["vat_display"] == format_aed(Decimal("15.00"))

    def test_payload_carries_trn_and_provider_choice(self):
        for prov in ("stripe", "telr", "tabby"):
            payload = to_provider_payload(self._inv(provider=prov))
            assert payload["provider"] == prov
            assert payload["seller_trn"] == "100123456700003"
            assert payload["customer"]["trn"] == "100987654300003"
            assert payload["currency"] == "AED"

    def test_payload_carries_iso_timestamps(self):
        payload = to_provider_payload(self._inv())
        # issued_at default is "now"; just check it parses.
        datetime.fromisoformat(payload["issued_at"])
        assert payload["due_at"] == "2026-06-01T00:00:00+00:00"
