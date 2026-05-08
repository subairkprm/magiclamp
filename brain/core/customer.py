"""Customer 360 v1 — profile, attachments, and timeline merger.

Phase-1 customer surface: a *single* record per customer per workspace,
the metadata of any attachments uploaded against that customer, and a
unified timeline that fuses fact-ledger writes, manual notes, channel
messages (WhatsApp / email / call), invoice events, and attachment
uploads into one chronologically-ordered stream.

This module is the pure-domain layer:

* It carries no DB or HTTP code — repositories layer feeds it dataclasses
  built from rows, the API layer renders them. That keeps tests trivial
  and lets the same code drive both the SQLite default backend and the
  Supabase one without branching.
* It enforces UAE-specific data hygiene at the *boundary* — Emirates IDs
  and mobile numbers are validated + normalised to canonical form on
  construction, so storage and downstream consumers can trust them.
* The timeline merger is order-stable, filterable, and bounded so a
  customer with 50k events can still page through their last 50.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence

from .uae_id import (
    format_emirates_id,
    is_valid_emirates_id,
    is_valid_uae_mobile,
    normalize_uae_mobile,
)


# ── Customer profile ────────────────────────────────────────────────


class CustomerSegment(str, Enum):
    """Where the customer sits in the funnel. ``str`` mixin → JSON-friendly."""

    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    CHURNED = "churned"

    @classmethod
    def parse(cls, value: "str | CustomerSegment") -> "CustomerSegment":
        """Case-insensitive parse from a string."""
        if isinstance(value, CustomerSegment):
            return value
        if not isinstance(value, str) or not value:
            raise ValueError(f"Invalid customer segment: {value!r}")
        try:
            return cls(value.strip().lower())
        except ValueError as e:
            raise ValueError(
                f"Unknown customer segment {value!r}; expected one of "
                f"{[s.value for s in cls]}"
            ) from e


# Languages we currently support for customer comms — keep narrow on
# purpose; adding a third should be a deliberate decision, not a typo.
_SUPPORTED_LANGUAGES: FrozenSet[str] = frozenset({"en", "ar"})


@dataclass
class CustomerProfile:
    """A single customer record, scoped to one workspace.

    ``emirates_id`` and ``mobile_e164`` are validated + normalised on
    construction. Storage layers should persist exactly what is on the
    object after ``__post_init__`` runs — never the raw input.
    """

    id: str
    workspace_id: str
    display_name: str
    segment: CustomerSegment = CustomerSegment.LEAD
    language: str = "en"
    emirates_id: Optional[str] = None
    mobile_e164: Optional[str] = None
    email: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("CustomerProfile.id must be non-empty")
        if not self.workspace_id or not str(self.workspace_id).strip():
            raise ValueError("CustomerProfile.workspace_id must be non-empty")
        if not self.display_name or not self.display_name.strip():
            raise ValueError("CustomerProfile.display_name must be non-empty")
        # Coerce + validate the segment so callers may pass a plain string.
        if not isinstance(self.segment, CustomerSegment):
            self.segment = CustomerSegment.parse(self.segment)
        # Language: bilingual surface (English + Arabic) is the Phase-1 scope.
        lang = (self.language or "").strip().lower()
        if lang not in _SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language {self.language!r}; expected one of "
                f"{sorted(_SUPPORTED_LANGUAGES)}"
            )
        self.language = lang
        # Normalise the optional EID to canonical "784-YYYY-NNNNNNN-C".
        if self.emirates_id is not None:
            if not is_valid_emirates_id(self.emirates_id):
                raise ValueError(f"Invalid Emirates ID: {self.emirates_id!r}")
            self.emirates_id = format_emirates_id(self.emirates_id)
        # Normalise the optional mobile to E.164 +9715XXXXXXXX.
        if self.mobile_e164 is not None:
            if not is_valid_uae_mobile(self.mobile_e164):
                raise ValueError(f"Invalid UAE mobile: {self.mobile_e164!r}")
            self.mobile_e164 = normalize_uae_mobile(self.mobile_e164)
        # Light email sanity — full RFC validation is the Pydantic
        # model's job at the API boundary; here we just refuse the
        # obviously-broken so audit logs stay readable.
        if self.email is not None:
            email = self.email.strip()
            if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
                raise ValueError(f"Invalid email: {self.email!r}")
            self.email = email.lower()
        # Deduplicate tags + drop empties; keep insertion order.
        seen: set = set()
        cleaned: List[str] = []
        for t in self.tags:
            if not isinstance(t, str):
                raise ValueError(f"CustomerProfile.tags must be strings, got {t!r}")
            t2 = t.strip().lower()
            if t2 and t2 not in seen:
                seen.add(t2)
                cleaned.append(t2)
        self.tags = cleaned


# ── Attachments ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class Attachment:
    """Metadata for a file uploaded against a customer.

    The actual blob lives in object storage (S3 / Supabase Storage). The
    repository layer is responsible for issuing signed URLs; this record
    only carries the integrity-relevant fields so the timeline can render
    a row without a second round-trip.
    """

    id: str
    customer_id: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in ("id", "customer_id", "filename", "content_type"):
            if not getattr(self, field_name) or not str(getattr(self, field_name)).strip():
                raise ValueError(f"Attachment.{field_name} must be non-empty")
        if self.size_bytes < 0:
            raise ValueError(f"Attachment.size_bytes must be non-negative, got {self.size_bytes}")
        # SHA-256 hex digests are always 64 lowercase hex chars. We're strict
        # because a bad checksum here is silently corrupting the integrity
        # signal we expose to the customer.
        digest = self.sha256.strip().lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"Attachment.sha256 must be a 64-char hex digest, got {self.sha256!r}")
        object.__setattr__(self, "sha256", digest)


# ── Timeline ────────────────────────────────────────────────────────


class TimelineEventKind(str, Enum):
    """The full set of event kinds the customer timeline can render."""

    FACT_ADDED = "fact_added"
    FACT_UPDATED = "fact_updated"
    FACT_DELETED = "fact_deleted"
    NOTE = "note"
    CALL = "call"
    WHATSAPP_IN = "whatsapp_in"
    WHATSAPP_OUT = "whatsapp_out"
    EMAIL_IN = "email_in"
    EMAIL_OUT = "email_out"
    INVOICE_ISSUED = "invoice_issued"
    INVOICE_PAID = "invoice_paid"
    ATTACHMENT_ADDED = "attachment_added"

    @classmethod
    def parse(cls, value: "str | TimelineEventKind") -> "TimelineEventKind":
        if isinstance(value, TimelineEventKind):
            return value
        if not isinstance(value, str) or not value:
            raise ValueError(f"Invalid timeline event kind: {value!r}")
        try:
            return cls(value.strip().lower())
        except ValueError as e:
            raise ValueError(
                f"Unknown timeline event kind {value!r}; expected one of "
                f"{[k.value for k in cls]}"
            ) from e


@dataclass(frozen=True)
class TimelineEvent:
    """One row on the customer timeline."""

    id: str
    customer_id: str
    occurred_at: datetime
    kind: TimelineEventKind
    summary: str
    actor: str = "system"  # user_id, "system", or integration name
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("TimelineEvent.id must be non-empty")
        if not self.customer_id or not str(self.customer_id).strip():
            raise ValueError("TimelineEvent.customer_id must be non-empty")
        if not self.summary or not self.summary.strip():
            raise ValueError("TimelineEvent.summary must be non-empty")
        if not isinstance(self.occurred_at, datetime):
            raise ValueError(
                f"TimelineEvent.occurred_at must be datetime, got {type(self.occurred_at).__name__}"
            )
        if self.occurred_at.tzinfo is None:
            # Force timezone-aware so sort + filter are unambiguous.
            raise ValueError("TimelineEvent.occurred_at must be timezone-aware")
        if not isinstance(self.kind, TimelineEventKind):
            object.__setattr__(self, "kind", TimelineEventKind.parse(self.kind))


def build_timeline(
    events: Iterable[TimelineEvent],
    *,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    kinds: Optional[Sequence["str | TimelineEventKind"]] = None,
    limit: Optional[int] = None,
) -> List[TimelineEvent]:
    """Merge, filter, and sort timeline events for one customer.

    Returns events in **descending occurred_at order** (newest first),
    which is what every front-end view of this expects.

    Parameters
    ----------
    events : iterable of TimelineEvent
        Already-loaded events from any source (fact ledger, audit log,
        WhatsApp, email, invoices, attachments). All must belong to the
        same customer — this function does not enforce that, leaving
        cross-customer leakage as a repository-layer concern.
    since, until : optional datetime
        Inclusive lower / upper bounds on ``occurred_at``. Both must be
        timezone-aware if provided.
    kinds : optional sequence
        If supplied, only events whose ``kind`` is in this set are
        returned. Strings and enum members are both accepted.
    limit : optional positive int
        Cap on the returned list length. Applied **after** sorting so
        you always get the newest ``limit`` events.
    """
    if since is not None and (not isinstance(since, datetime) or since.tzinfo is None):
        raise ValueError("`since` must be a timezone-aware datetime")
    if until is not None and (not isinstance(until, datetime) or until.tzinfo is None):
        raise ValueError("`until` must be a timezone-aware datetime")
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        raise ValueError(f"`limit` must be a positive int, got {limit!r}")

    if kinds is not None:
        kind_set: Optional[FrozenSet[TimelineEventKind]] = frozenset(
            TimelineEventKind.parse(k) for k in kinds
        )
    else:
        kind_set = None

    filtered: List[TimelineEvent] = []
    for ev in events:
        if since is not None and ev.occurred_at < since:
            continue
        if until is not None and ev.occurred_at > until:
            continue
        if kind_set is not None and ev.kind not in kind_set:
            continue
        filtered.append(ev)

    # Sort newest-first; tie-break by id so the order is fully deterministic.
    filtered.sort(key=lambda e: (e.occurred_at, e.id), reverse=True)

    if limit is not None:
        filtered = filtered[:limit]
    return filtered


__all__ = [
    "CustomerSegment",
    "CustomerProfile",
    "Attachment",
    "TimelineEventKind",
    "TimelineEvent",
    "build_timeline",
]
