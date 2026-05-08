"""UAE identity helpers — Emirates ID + UAE mobile validation / formatting.

Customer 360 (Phase 1) is the first surface that ingests these two
identifiers from real users. Centralising the validation + canonical
formatting here means the API, the WhatsApp ingester, the CSV importer
and the future Next.js form all agree on what "valid" means and what the
canonical stored form looks like — without each carrying a regex copy.

Emirates ID (EID), as issued by the Federal Authority for Identity,
Citizenship, Customs and Port Security (ICP):

* Always 15 digits, conventionally written ``784-YYYY-NNNNNNN-C``.
* The leading **784** is the ISO-3166 numeric for the UAE.
* ``YYYY`` is the holder's year of birth.
* ``NNNNNNN`` is a 7-digit serial.
* ``C`` is a single check digit computed with the **Luhn** algorithm
  over the first 14 digits (this is the same algorithm credit-card
  numbers use). The ICP validator on https://id.gov.ae uses Luhn; we
  match that so an EID that fails here will also fail the official site.

UAE mobile numbers:

* E.164 form is ``+9715XXXXXXXX`` — country code 971, mobile prefix 5,
  then 8 digits (often written 050/052/054/055/056/058 locally).
* This module accepts the local 9-digit form (``05XXXXXXXX``), the
  10-digit ``9715XXXXXXXX``, and the canonical ``+9715XXXXXXXX`` form,
  with arbitrary spaces / dashes / parentheses, and normalises all of
  them to E.164.
"""

from __future__ import annotations

import re
from typing import Final


# ── Emirates ID ─────────────────────────────────────────────────────

_EID_DIGITS_RE: Final = re.compile(r"\D+")
_EID_PREFIX: Final = "784"


def _digits_only(value: str) -> str:
    """Strip everything that isn't a digit."""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    return _EID_DIGITS_RE.sub("", value)


def _luhn_checksum_ok(digits: str) -> bool:
    """Standard Luhn validation over an all-digit string."""
    total = 0
    # Process right-to-left; double every second digit.
    for i, ch in enumerate(reversed(digits)):
        n = ord(ch) - 48  # ord('0') == 48
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def is_valid_emirates_id(value: str) -> bool:
    """Return True iff ``value`` is a structurally + checksum-valid EID.

    Accepts the number with or without dashes/spaces. Year-of-birth is
    sanity-checked to a plausible range (1900–2099) so a typo like
    ``784-0000-...`` is rejected even though it would Luhn-check.
    """
    try:
        digits = _digits_only(value)
    except TypeError:
        return False
    if len(digits) != 15:
        return False
    if not digits.startswith(_EID_PREFIX):
        return False
    year = int(digits[3:7])
    if not (1900 <= year <= 2099):
        return False
    return _luhn_checksum_ok(digits)


def format_emirates_id(value: str) -> str:
    """Return ``value`` in the canonical ``784-YYYY-NNNNNNN-C`` form.

    Raises ``ValueError`` if ``value`` is not a valid EID — callers that
    want a soft check should call :func:`is_valid_emirates_id` first.
    """
    digits = _digits_only(value) if isinstance(value, str) else ""
    if not is_valid_emirates_id(digits):
        raise ValueError(f"Invalid Emirates ID: {value!r}")
    return f"{digits[0:3]}-{digits[3:7]}-{digits[7:14]}-{digits[14]}"


# ── UAE mobile numbers ──────────────────────────────────────────────

# Valid mobile-prefix second digit. Per the TRA 2024 numbering plan the
# allocated mobile prefixes are 50/52/54/55/56/58 (51/53/57/59 are
# unassigned / reserved). We're conservative — adding a freshly-allocated
# prefix here is a one-line change.
_VALID_MOBILE_PREFIXES: Final = frozenset({"50", "52", "54", "55", "56", "58"})


def normalize_uae_mobile(value: str) -> str:
    """Normalise ``value`` to E.164 form ``+9715XXXXXXXX``.

    Raises ``ValueError`` if it can't be parsed as a UAE mobile.
    Accepts:

    * ``+971 50 123 4567``  (E.164 with separators)
    * ``00971501234567``    (international dialling prefix)
    * ``971501234567``      (without leading +)
    * ``0501234567``        (national trunk-zero form)
    * ``501234567``         (subscriber-only)

    All separators (spaces, dashes, parentheses) are tolerated.
    """
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    digits = _digits_only(value)
    # Strip the international "00" if present.
    if digits.startswith("00"):
        digits = digits[2:]
    # Strip the country code if present.
    if digits.startswith("971"):
        digits = digits[3:]
    # Strip the national trunk zero if present.
    if digits.startswith("0"):
        digits = digits[1:]
    # We should now be left with the 9-digit subscriber number "5XXXXXXXX".
    if len(digits) != 9 or not digits.startswith("5"):
        raise ValueError(f"Not a UAE mobile number: {value!r}")
    if digits[0:2] not in _VALID_MOBILE_PREFIXES:
        raise ValueError(
            f"Not a UAE mobile number ({digits[0:2]} is not an allocated "
            f"mobile prefix): {value!r}"
        )
    return "+971" + digits


def is_valid_uae_mobile(value: str) -> bool:
    """Soft check — True iff :func:`normalize_uae_mobile` would succeed."""
    try:
        normalize_uae_mobile(value)
    except (ValueError, TypeError):
        return False
    return True


__all__ = [
    "is_valid_emirates_id",
    "format_emirates_id",
    "is_valid_uae_mobile",
    "normalize_uae_mobile",
]
