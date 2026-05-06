"""
Tests for the SQLite DatabaseClient backend.

Verifies that ``SQLiteClient`` honours the same QueryResult contract as
``SupabaseClient`` so repositories work unchanged on either backend, and that
the bundled schema is bootstrapped on startup.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add brain to path (mirrors other tests)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

# Ensure required settings exist before importing modules that read them.
os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")


@pytest.fixture
def tmp_db(tmp_path):
    db_file = tmp_path / "ml_test.db"
    from core.database_sqlite import SQLiteClient

    return SQLiteClient(db_path=str(db_file))


class TestSchemaBootstrap:
    def test_schema_creates_expected_tables(self, tmp_db):
        # Sanity: a couple of representative tables must exist after init.
        with tmp_db._lock:
            rows = tmp_db._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        names = {r[0] for r in rows}
        assert {"users", "brain_facts", "organizations", "llm_settings"}.issubset(names)


class TestInsertSelectRoundtrip:
    def test_insert_assigns_uuid_and_returns_row(self, tmp_db):
        res = tmp_db.insert(
            table="organizations",
            data={"name": "Acme", "slug": "acme", "plan": "free"},
        )
        assert res.success
        assert res.data and res.data[0]["name"] == "Acme"
        # UUID assigned automatically.
        assert res.data[0]["id"]
        # is_active surfaces as bool, not int.
        assert res.data[0]["is_active"] is True

    def test_select_filters_by_tenant_id(self, tmp_db):
        tmp_db.insert(
            table="brain_facts",
            data={"key": "k1", "value": {"v": 1}},
            tenant_id="t-A",
        )
        tmp_db.insert(
            table="brain_facts",
            data={"key": "k2", "value": {"v": 2}},
            tenant_id="t-B",
        )
        a = tmp_db.select(table="brain_facts", tenant_id="t-A")
        b = tmp_db.select(table="brain_facts", tenant_id="t-B")
        assert len(a.data) == 1 and a.data[0]["key"] == "k1"
        # JSON column round-trips back to a dict.
        assert a.data[0]["value"] == {"v": 1}
        assert len(b.data) == 1 and b.data[0]["key"] == "k2"

    def test_select_count_and_order(self, tmp_db):
        for i in range(3):
            tmp_db.insert(
                table="brain_facts",
                data={"key": f"k{i}", "value": i, "confidence": i * 0.3},
                tenant_id="t",
            )
        res = tmp_db.select(
            table="brain_facts",
            tenant_id="t",
            order_by="confidence.desc",
            count=True,
        )
        assert res.count == 3
        assert [r["key"] for r in res.data] == ["k2", "k1", "k0"]

    def test_select_unsafe_order_by_rejected(self, tmp_db):
        # SQL-injection guard on the order_by string.
        res = tmp_db.select(
            table="brain_facts", tenant_id="t", order_by="key; DROP TABLE users"
        )
        assert not res.success
        assert "Unsafe order_by" in (res.error or "")


class TestUpsert:
    def test_upsert_creates_then_updates_on_conflict(self, tmp_db):
        first = tmp_db.upsert(
            table="brain_facts",
            data={"key": "color", "value": "red", "confidence": 0.5},
            tenant_id="t",
        )
        assert first.success and first.data
        second = tmp_db.upsert(
            table="brain_facts",
            data={"key": "color", "value": "blue", "confidence": 0.9},
            tenant_id="t",
        )
        assert second.data[0]["value"] == "blue"
        assert second.data[0]["confidence"] == pytest.approx(0.9)
        # Same row, not a duplicate.
        assert second.data[0]["id"] == first.data[0]["id"]
        all_rows = tmp_db.select(table="brain_facts", tenant_id="t")
        assert len(all_rows.data) == 1


class TestUpdateDelete:
    def test_update_filters_by_tenant(self, tmp_db):
        tmp_db.insert(table="brain_facts", data={"key": "k", "value": 1}, tenant_id="t")
        tmp_db.insert(table="brain_facts", data={"key": "k", "value": 2}, tenant_id="other")
        tmp_db.update(
            table="brain_facts",
            data={"value": 99},
            tenant_id="t",
            filters={"key": "k"},
        )
        t_rows = tmp_db.select(table="brain_facts", tenant_id="t")
        other_rows = tmp_db.select(table="brain_facts", tenant_id="other")
        assert t_rows.data[0]["value"] == 99
        assert other_rows.data[0]["value"] == 2  # untouched

    def test_delete_filters_by_tenant(self, tmp_db):
        tmp_db.insert(table="brain_facts", data={"key": "k", "value": 1}, tenant_id="t")
        tmp_db.insert(table="brain_facts", data={"key": "k", "value": 2}, tenant_id="other")
        tmp_db.delete(table="brain_facts", tenant_id="t", filters={"key": "k"})
        assert tmp_db.count(table="brain_facts", tenant_id="t") == 0
        assert tmp_db.count(table="brain_facts", tenant_id="other") == 1


class TestRepositoryCompatibility:
    """The SQLite backend must be drop-in compatible with FactRepository."""

    def test_fact_repository_save_get_delete(self, tmp_db):
        from repositories.fact import FactRepository

        repo = FactRepository(tmp_db)
        saved = repo.save_fact(key="city", value="dubai", tenant_id="t")
        assert saved.value == "dubai"

        recent = repo.get_recent_facts(tenant_id="t")
        assert len(recent) == 1 and recent[0].key == "city"

        # Upsert behaviour (same key) must update in place.
        repo.save_fact(key="city", value="abu-dhabi", tenant_id="t")
        again = repo.get_recent_facts(tenant_id="t")
        assert len(again) == 1 and again[0].value == "abu-dhabi"

        repo.delete(key="city", tenant_id="t")
        assert repo.count(tenant_id="t") == 0


class TestGetClientBackendSelection:
    def test_get_client_returns_sqlite_when_db_backend_sqlite(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BRAIN_DATA_DIR", str(tmp_path))
        # Reset singleton to force a fresh selection.
        from core import database as db_mod

        monkeypatch.setattr(db_mod, "_db_client", None)
        from core.config import settings

        monkeypatch.setattr(settings, "DB_BACKEND", "sqlite")
        monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))

        client = db_mod.get_database_client()
        from core.database_sqlite import SQLiteClient

        assert isinstance(client, SQLiteClient)
        # Reset for other tests.
        monkeypatch.setattr(db_mod, "_db_client", None)
