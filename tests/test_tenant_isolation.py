"""Multi-tenant isolation audit at the repository layer.

The SQLite backend's tenant filter is exercised by ``test_sqlite_backend.py``;
this file goes one layer up and asserts the same guarantee through
``FactRepository`` — the actual seam business code goes through. It is the
test the Backend/API + Security agents own (see SUBAGENTS.md → "DoD: 0 tenant
leaks") and is wired into the CI quality gates from ROADMAP.md.

Tenants A and B never see each other's facts on any read path
(``get_recent_facts``, ``get_by_key``, ``get_all``), one tenant's
``save_fact`` cannot overwrite another's record with the same key, and one
tenant's ``delete`` cannot remove another tenant's row.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    # Force RAG off so the repo doesn't try to spin up a vector store and so
    # the assertions stay focused on the SQL multi-tenant path.
    monkeypatch.setenv("RAG_ENABLED", "false")
    from core.config import settings

    monkeypatch.setattr(settings, "RAG_ENABLED", False)

    from core.database_sqlite import SQLiteClient
    from repositories.fact import FactRepository

    db = SQLiteClient(db_path=str(tmp_path / "iso.db"))
    return FactRepository(db_client=db)


# Two distinct tenant ids used across all tests below.
T_A = "tenant-A"
T_B = "tenant-B"


class TestCrossTenantIsolation:
    def test_get_recent_returns_only_calling_tenants_rows(self, repo):
        repo.save_fact(key="region", value="dubai", tenant_id=T_A)
        repo.save_fact(key="region", value="abudhabi", tenant_id=T_B)

        a = repo.get_recent_facts(tenant_id=T_A)
        b = repo.get_recent_facts(tenant_id=T_B)

        assert {f.value for f in a} == {"dubai"}
        assert {f.value for f in b} == {"abudhabi"}

    def test_get_by_key_does_not_leak_other_tenants_value(self, repo):
        # Same key, different tenant — a classic cross-tenant lookup attack.
        repo.save_fact(key="vip_score", value="A+", tenant_id=T_A)
        repo.save_fact(key="vip_score", value="C", tenant_id=T_B)

        a = repo.get_by_key("vip_score", tenant_id=T_A)
        b = repo.get_by_key("vip_score", tenant_id=T_B)

        assert a is not None and a.value == "A+"
        assert b is not None and b.value == "C"

    def test_get_by_key_returns_none_when_only_other_tenant_has_it(self, repo):
        repo.save_fact(key="secret-only-in-a", value="hush", tenant_id=T_A)
        # Tenant B never wrote this key; lookup must miss.
        assert repo.get_by_key("secret-only-in-a", tenant_id=T_B) is None

    def test_get_all_returns_only_calling_tenants_rows(self, repo):
        for k in ("a", "b", "c"):
            repo.save_fact(key=k, value=k.upper(), tenant_id=T_A)
        repo.save_fact(key="z", value="Z", tenant_id=T_B)

        a_keys = {f.key for f in repo.get_all(tenant_id=T_A)}
        b_keys = {f.key for f in repo.get_all(tenant_id=T_B)}

        assert a_keys == {"a", "b", "c"}
        assert b_keys == {"z"}

    def test_save_does_not_overwrite_other_tenants_row_with_same_key(self, repo):
        # Both tenants store a fact under the same key — the on-conflict
        # clause must be scoped to (key, tenant_id), not key alone.
        repo.save_fact(key="kyc-status", value="approved", tenant_id=T_A)
        repo.save_fact(key="kyc-status", value="pending", tenant_id=T_B)

        a = repo.get_by_key("kyc-status", tenant_id=T_A)
        b = repo.get_by_key("kyc-status", tenant_id=T_B)
        assert a is not None and a.value == "approved"
        assert b is not None and b.value == "pending"

        # And a second update inside tenant A must not touch tenant B.
        repo.save_fact(key="kyc-status", value="rejected", tenant_id=T_A)
        a2 = repo.get_by_key("kyc-status", tenant_id=T_A)
        b2 = repo.get_by_key("kyc-status", tenant_id=T_B)
        assert a2 is not None and a2.value == "rejected"
        assert b2 is not None and b2.value == "pending"  # untouched

    def test_delete_in_one_tenant_does_not_remove_other_tenants_row(self, repo):
        repo.save_fact(key="opt-in", value="yes", tenant_id=T_A)
        repo.save_fact(key="opt-in", value="yes", tenant_id=T_B)

        # Tenant A deletes its row; tenant B's row must survive intact.
        assert repo.delete(key="opt-in", tenant_id=T_A) is True
        assert repo.get_by_key("opt-in", tenant_id=T_A) is None

        b = repo.get_by_key("opt-in", tenant_id=T_B)
        assert b is not None and b.value == "yes"

    def test_delete_with_wrong_tenant_does_not_remove_target_row(self, repo):
        # An attacker controlling tenant B passes A's key. Even though the
        # fact exists *somewhere*, the call must not delete it.
        repo.save_fact(key="balance", value=1000, tenant_id=T_A)
        repo.delete(key="balance", tenant_id=T_B)  # may return True (no rows)

        a = repo.get_by_key("balance", tenant_id=T_A)
        assert a is not None and a.value == 1000
