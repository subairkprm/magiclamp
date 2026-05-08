"""Tests for brain/core/customer.py — Customer 360 v1 domain."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from core.customer import (  # noqa: E402
    Attachment,
    CustomerProfile,
    CustomerSegment,
    TimelineEvent,
    TimelineEventKind,
    build_timeline,
)


VALID_EID = "784198512345673"
SHA = "a" * 64


# ── CustomerSegment ─────────────────────────────────────────────────


class TestCustomerSegment:
    @pytest.mark.parametrize("raw", ["lead", "Lead", " CUSTOMER ", "prospect", "churned"])
    def test_parse_accepts_case_insensitive(self, raw):
        assert isinstance(CustomerSegment.parse(raw), CustomerSegment)

    @pytest.mark.parametrize("bad", ["", "vip", None, 5])
    def test_parse_rejects_unknown(self, bad):
        with pytest.raises(ValueError):
            CustomerSegment.parse(bad)


# ── CustomerProfile ─────────────────────────────────────────────────


class TestCustomerProfile:
    def _ok(self, **over):
        kwargs = dict(
            id="cust-1", workspace_id="ws-1", display_name="Aisha Al Mansoori"
        )
        kwargs.update(over)
        return CustomerProfile(**kwargs)

    def test_minimal_fields_default_to_lead_english(self):
        p = self._ok()
        assert p.segment is CustomerSegment.LEAD
        assert p.language == "en"
        assert p.tags == []

    def test_segment_string_is_coerced(self):
        assert self._ok(segment="customer").segment is CustomerSegment.CUSTOMER

    def test_eid_is_normalised_to_canonical_form(self):
        p = self._ok(emirates_id="784 1985 1234567 3")
        assert p.emirates_id == "784-1985-1234567-3"

    def test_invalid_eid_rejected(self):
        with pytest.raises(ValueError, match="Emirates ID"):
            self._ok(emirates_id="784-0000-0000000-0")

    def test_mobile_is_normalised_to_e164(self):
        p = self._ok(mobile_e164="0501234567")
        assert p.mobile_e164 == "+971501234567"

    def test_invalid_mobile_rejected(self):
        with pytest.raises(ValueError, match="UAE mobile"):
            self._ok(mobile_e164="+97143434343")

    def test_email_lowercased_and_validated(self):
        p = self._ok(email="Aisha@Example.AE")
        assert p.email == "aisha@example.ae"
        with pytest.raises(ValueError, match="email"):
            self._ok(email="not-an-email")

    def test_unsupported_language_rejected(self):
        with pytest.raises(ValueError, match="language"):
            self._ok(language="fr")

    @pytest.mark.parametrize("lang", ["en", "ar", "EN", "AR"])
    def test_supported_languages_accepted(self, lang):
        assert self._ok(language=lang).language == lang.lower()

    def test_tags_deduped_lowercased_and_trimmed(self):
        p = self._ok(tags=["VIP", "vip", "  Banking ", "banking", ""])
        assert p.tags == ["vip", "banking"]

    def test_required_string_fields_must_be_non_empty(self):
        for field in ("id", "workspace_id", "display_name"):
            with pytest.raises(ValueError, match=field):
                self._ok(**{field: "  "})


# ── Attachment ──────────────────────────────────────────────────────


class TestAttachment:
    def _ok(self, **over):
        kwargs = dict(
            id="att-1",
            customer_id="cust-1",
            filename="contract.pdf",
            content_type="application/pdf",
            size_bytes=1234,
            sha256=SHA,
        )
        kwargs.update(over)
        return Attachment(**kwargs)

    def test_basic_construction(self):
        att = self._ok()
        assert att.size_bytes == 1234
        assert att.sha256 == SHA

    def test_rejects_negative_size(self):
        with pytest.raises(ValueError, match="size_bytes"):
            self._ok(size_bytes=-1)

    def test_rejects_bad_sha256(self):
        for bad in ("", "deadbeef", "g" * 64, "A" * 63):
            with pytest.raises(ValueError, match="sha256"):
                self._ok(sha256=bad)

    def test_uppercase_sha_is_normalised_to_lowercase(self):
        att = self._ok(sha256="A" * 64)
        assert att.sha256 == "a" * 64

    @pytest.mark.parametrize("field", ["id", "customer_id", "filename", "content_type"])
    def test_required_strings_must_be_non_empty(self, field):
        with pytest.raises(ValueError, match=field):
            self._ok(**{field: "  "})


# ── Timeline ────────────────────────────────────────────────────────


def _ev(eid, kind, when, **extra):
    return TimelineEvent(
        id=eid,
        customer_id="cust-1",
        occurred_at=when,
        kind=TimelineEventKind.parse(kind),
        summary=extra.get("summary", "x"),
        actor=extra.get("actor", "system"),
        payload=extra.get("payload", {}),
    )


class TestTimelineEvent:
    def test_requires_timezone_aware_datetime(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            _ev("e1", "note", datetime(2026, 1, 1))

    def test_kind_string_is_coerced(self):
        e = _ev("e1", "fact_added", datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert e.kind is TimelineEventKind.FACT_ADDED


class TestBuildTimeline:
    def setup_method(self):
        t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.events = [
            _ev("e1", "note", t0),
            _ev("e2", "fact_added", t0 + timedelta(hours=1)),
            _ev("e3", "whatsapp_in", t0 + timedelta(hours=2)),
            _ev("e4", "invoice_issued", t0 + timedelta(hours=3)),
            _ev("e5", "attachment_added", t0 + timedelta(hours=4)),
        ]
        self.t0 = t0

    def test_returns_newest_first(self):
        out = build_timeline(self.events)
        assert [e.id for e in out] == ["e5", "e4", "e3", "e2", "e1"]

    def test_filters_by_since_and_until_inclusive(self):
        out = build_timeline(
            self.events,
            since=self.t0 + timedelta(hours=1),
            until=self.t0 + timedelta(hours=3),
        )
        assert [e.id for e in out] == ["e4", "e3", "e2"]

    def test_filters_by_kind_set_with_strings_or_enums(self):
        out = build_timeline(
            self.events,
            kinds=["whatsapp_in", TimelineEventKind.INVOICE_ISSUED],
        )
        assert [e.id for e in out] == ["e4", "e3"]

    def test_limit_returns_newest_n(self):
        out = build_timeline(self.events, limit=2)
        assert [e.id for e in out] == ["e5", "e4"]

    def test_limit_must_be_positive(self):
        with pytest.raises(ValueError, match="limit"):
            build_timeline(self.events, limit=0)

    def test_since_until_must_be_tz_aware(self):
        with pytest.raises(ValueError, match="since"):
            build_timeline(self.events, since=datetime(2026, 1, 1))
        with pytest.raises(ValueError, match="until"):
            build_timeline(self.events, until=datetime(2026, 1, 1))

    def test_empty_input_returns_empty_list(self):
        assert build_timeline([]) == []

    def test_tie_break_is_deterministic_by_id(self):
        # Two events at exactly the same instant — secondary sort is by id desc.
        same = self.t0
        evs = [_ev("a", "note", same), _ev("b", "note", same), _ev("c", "note", same)]
        out = build_timeline(evs)
        assert [e.id for e in out] == ["c", "b", "a"]
