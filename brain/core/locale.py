"""UAE locale helpers — AED currency, VAT, Arabic-Indic digits.

Small, dependency-free utilities used by billing, invoice rendering, and any
user-facing surface that needs UAE-correct money / number formatting. Kept
deliberately minimal so it can be reused by both the FastAPI brain and any
future Next.js / Electron renderer through a thin shim.

Conventions backed by the UAE Federal Tax Authority:

* The standard VAT rate is **5 %** (Federal Decree-Law 8 of 2017).
* Tax invoices must show the VAT amount and the gross total separately and
  in AED — even when the underlying transaction is in another currency.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

#: UAE standard VAT rate (5 %), as a Decimal for exact arithmetic.
VAT_RATE_UAE: Final[Decimal] = Decimal("0.05")

#: Mapping table from Western (Arabic) digits to Eastern Arabic-Indic digits
#: (U+0660…U+0669) — used when the user opts into Arabic-Indic numerals.
_ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _to_decimal(amount) -> Decimal:
    """Best-effort coercion to a non-negative ``Decimal`` for money math.

    Accepts ``int``, ``float``, ``str`` or ``Decimal``. Floats are stringified
    first to avoid binary-float surprises (``0.1 + 0.2`` etc.).
    """
    if isinstance(amount, Decimal):
        d = amount
    elif isinstance(amount, (int, str)):
        d = Decimal(amount)
    elif isinstance(amount, float):
        d = Decimal(str(amount))
    else:  # pragma: no cover - defensive
        raise TypeError(f"Unsupported amount type: {type(amount).__name__}")
    if d < 0:
        raise ValueError("Monetary amounts must be non-negative")
    return d


def _quantise(amount: Decimal) -> Decimal:
    """Round to 2 decimal places using banker-friendly half-up rounding."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class VATBreakdown:
    """A VAT-compliant breakdown of a sale, all in AED.

    All three fields are quantised to 2 decimal places. Invariant:
    ``net + vat == gross`` (after rounding).
    """

    net: Decimal
    vat: Decimal
    gross: Decimal
    rate: Decimal = VAT_RATE_UAE


def compute_vat(net_amount, rate: Decimal = VAT_RATE_UAE) -> VATBreakdown:
    """Return a :class:`VATBreakdown` for a *net* (pre-tax) amount.

    >>> compute_vat("100")
    VATBreakdown(net=Decimal('100.00'), vat=Decimal('5.00'), gross=Decimal('105.00'), rate=Decimal('0.05'))
    """
    net = _quantise(_to_decimal(net_amount))
    vat = _quantise(net * rate)
    gross = _quantise(net + vat)
    return VATBreakdown(net=net, vat=vat, gross=gross, rate=rate)


def format_aed(amount, *, arabic_indic_digits: bool = False) -> str:
    """Format ``amount`` as a UAE-style AED money string.

    Examples:
        >>> format_aed(1234.5)
        'AED 1,234.50'
        >>> format_aed(99, arabic_indic_digits=True)
        'AED ٩٩٫٠٠'

    When ``arabic_indic_digits=True`` the comma/period separators are also
    swapped for the Arabic-Indic ones (U+066B Arabic decimal separator,
    U+066C Arabic thousands separator) so the output round-trips through an
    Arabic locale renderer cleanly.
    """
    value = _quantise(_to_decimal(amount))
    formatted = f"{value:,.2f}"
    if arabic_indic_digits:
        formatted = formatted.translate(_ARABIC_INDIC)
        formatted = formatted.replace(",", "\u066c").replace(".", "\u066b")
    return f"AED {formatted}"


__all__ = [
    "VAT_RATE_UAE",
    "VATBreakdown",
    "compute_vat",
    "format_aed",
]
