"""Billing pipeline scaffold — provider-agnostic UAE invoice builder.

Phase 1 of the UAE-market plan calls for a Stripe + Telr + Tabby billing
pipeline with **AED-default invoices** computed via
:func:`core.locale.compute_vat`. This module is the *provider-agnostic*
core of that pipeline:

* It models an invoice as plain data (``InvoiceLine``, ``Invoice``).
* It builds a normalised, JSON-serialisable invoice dict that any of the
  three payment-gateway adapters can post to its API as-is.
* It enforces UAE FTA tax-invoice fields (TRN, AED currency, separate
  VAT line) without taking a runtime dependency on any HTTP SDK.

The actual HTTP adapters (``brain/integrations/billing/stripe.py`` etc.)
will land in a follow-up slice; keeping the calculation layer here means
they only need to translate the dict, never re-do the math.

Why three providers, briefly:

* **Stripe** — global cards; required by SaaS-savvy SMEs (the bulk of the
  Standard tier).
* **Telr** — UAE-licensed gateway; required by buyers that mandate a local
  acquirer for PDPL / regulator reasons (Sovereign tier overlap).
* **Tabby** — BNPL ("buy now pay later"), now ubiquitous across UAE
  e-commerce; we accept it as a top-up payment method, not a subscription
  rail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from .locale import VAT_RATE_UAE, compute_vat, format_aed


class BillingProvider(str, Enum):
    """Supported payment gateways. Order matches GTM priority."""

    STRIPE = "stripe"
    TELR = "telr"
    TABBY = "tabby"

    @classmethod
    def parse(cls, value: "str | BillingProvider") -> "BillingProvider":
        """Case-insensitive parse from a string."""
        if isinstance(value, BillingProvider):
            return value
        if not isinstance(value, str) or not value:
            raise ValueError(f"Invalid billing provider: {value!r}")
        try:
            return cls(value.strip().lower())
        except ValueError as e:
            raise ValueError(
                f"Unknown billing provider {value!r}; expected one of "
                f"{[p.value for p in cls]}"
            ) from e


@dataclass(frozen=True)
class InvoiceLine:
    """One billable line item.

    ``unit_price_aed`` is the *net* (pre-VAT) unit price in AED. The line
    total is ``quantity * unit_price_aed``; VAT is computed at the invoice
    level so a single rate change doesn't have to ripple through every line.
    """

    description: str
    quantity: int
    unit_price_aed: Decimal

    def __post_init__(self) -> None:
        if not self.description or not self.description.strip():
            raise ValueError("InvoiceLine.description must not be empty")
        if self.quantity <= 0:
            raise ValueError(
                f"InvoiceLine.quantity must be positive, got {self.quantity}"
            )
        # Coerce numeric inputs to Decimal so callers can pass int/float/str.
        object.__setattr__(self, "unit_price_aed", Decimal(str(self.unit_price_aed)))
        if self.unit_price_aed < 0:
            raise ValueError(
                f"InvoiceLine.unit_price_aed must be non-negative, "
                f"got {self.unit_price_aed}"
            )

    @property
    def line_total_aed(self) -> Decimal:
        """Net (pre-VAT) total for this line, in AED."""
        return Decimal(self.quantity) * self.unit_price_aed


@dataclass
class Invoice:
    """A fully-priced AED invoice ready to hand to a payment provider."""

    invoice_number: str
    workspace_id: str
    customer_name: str
    lines: List[InvoiceLine]
    provider: BillingProvider
    currency: str = "AED"
    vat_rate: Decimal = VAT_RATE_UAE
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_at: Optional[datetime] = None
    seller_trn: Optional[str] = None  # Tax Registration Number, FTA-issued
    customer_trn: Optional[str] = None
    notes: Optional[str] = None

    # Computed totals — set by build_invoice / __post_init__.
    net_total_aed: Decimal = field(default=Decimal("0.00"))
    vat_total_aed: Decimal = field(default=Decimal("0.00"))
    gross_total_aed: Decimal = field(default=Decimal("0.00"))

    def __post_init__(self) -> None:
        if self.currency != "AED":
            # We only support AED in the scaffold — multi-currency comes
            # later with FX snapshotting. Failing loudly here stops a
            # caller from silently producing a non-FTA-compliant invoice.
            raise ValueError(
                f"Only AED is supported in the Phase-1 scaffold (got {self.currency!r})"
            )
        if not self.lines:
            raise ValueError("Invoice must have at least one line")
        net = sum((line.line_total_aed for line in self.lines), Decimal("0"))
        breakdown = compute_vat(net, rate=self.vat_rate)
        self.net_total_aed = breakdown.net
        self.vat_total_aed = breakdown.vat
        self.gross_total_aed = breakdown.gross


def build_invoice(
    *,
    invoice_number: str,
    workspace_id: str,
    customer_name: str,
    lines: Sequence[InvoiceLine],
    provider: "str | BillingProvider",
    seller_trn: Optional[str] = None,
    customer_trn: Optional[str] = None,
    vat_rate: Decimal = VAT_RATE_UAE,
    due_at: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> Invoice:
    """Create an :class:`Invoice`, validating + summing in one place.

    This is the function FastAPI handlers should call — it fixes the
    keyword interface even if ``Invoice``'s positional layout grows fields
    later, and it parses ``provider`` from a raw string for ergonomics.
    """
    return Invoice(
        invoice_number=invoice_number,
        workspace_id=workspace_id,
        customer_name=customer_name,
        lines=list(lines),
        provider=BillingProvider.parse(provider),
        seller_trn=seller_trn,
        customer_trn=customer_trn,
        vat_rate=vat_rate,
        due_at=due_at,
        notes=notes,
    )


def to_provider_payload(invoice: Invoice) -> Dict[str, Any]:
    """Render ``invoice`` as a JSON-serialisable dict.

    The shape is intentionally provider-agnostic — Stripe's
    ``InvoiceItem`` API, Telr's hosted-page payload, and Tabby's
    ``checkout`` payload can all be derived from this dict by their
    respective adapters with one mapping function each. Money is rendered
    in *fils* (1 AED = 100 fils) because all three providers want integer
    minor-units, never floats.

    Display strings are pre-rendered via ``format_aed`` so any UI surface
    that shows the invoice gets identical, locale-correct output without
    re-implementing the formatter.
    """
    return {
        "invoice_number": invoice.invoice_number,
        "workspace_id": invoice.workspace_id,
        "customer": {
            "name": invoice.customer_name,
            "trn": invoice.customer_trn,
        },
        "seller_trn": invoice.seller_trn,
        "currency": invoice.currency,
        "provider": invoice.provider.value,
        "issued_at": invoice.issued_at.isoformat(),
        "due_at": invoice.due_at.isoformat() if invoice.due_at else None,
        "notes": invoice.notes,
        "lines": [
            {
                "description": line.description,
                "quantity": line.quantity,
                "unit_price_fils": int(line.unit_price_aed * 100),
                "line_total_fils": int(line.line_total_aed * 100),
                "unit_price_display": format_aed(line.unit_price_aed),
            }
            for line in invoice.lines
        ],
        "totals": {
            "net_fils": int(invoice.net_total_aed * 100),
            "vat_fils": int(invoice.vat_total_aed * 100),
            "gross_fils": int(invoice.gross_total_aed * 100),
            "vat_rate": str(invoice.vat_rate),
            "net_display": format_aed(invoice.net_total_aed),
            "vat_display": format_aed(invoice.vat_total_aed),
            "gross_display": format_aed(invoice.gross_total_aed),
        },
    }


__all__ = [
    "BillingProvider",
    "InvoiceLine",
    "Invoice",
    "build_invoice",
    "to_provider_payload",
]
