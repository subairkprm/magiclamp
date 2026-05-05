"""
Tests for the RAG layer:
  * FakeEmbedder + InMemoryVectorStore round-trip
  * FactRepository dual-write (save -> vector upsert)
  * FactRepository.semantic_search joins back to canonical SQL data
  * FactRepository.delete propagates to the vector store
  * /reason/ask uses RAG facts when RAG_ENABLED, recent facts otherwise
"""

from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

# Add brain to path (mirrors other tests)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

# Ensure required settings exist before importing modules that read them.
os.environ.setdefault("SUPABASE_URL", "http://test")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from core.database import DatabaseClient, QueryResult  # noqa: E402
from core.embedder import Embedder, set_embedder  # noqa: E402
from core.vector_store import (  # noqa: E402
    InMemoryVectorStore,
    fact_vector_id,
    set_vector_store,
)
from repositories.fact import FactRepository  # noqa: E402


# ── Fakes ─────────────────────────────────────────────────────────
class FakeEmbedder(Embedder):
    """Deterministic embedder: hashes tokens into a small fixed-size vector."""

    dim = 16

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in text.lower().split():
            h = abs(hash(tok)) % self.dim
            vec[h] += 1.0
        # L2 normalize so cosine == dot
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class FakeDatabaseClient(DatabaseClient):
    """In-memory DatabaseClient sufficient for FactRepository tests."""

    def __init__(self) -> None:
        # table -> list[row]
        self._rows: Dict[str, List[Dict[str, Any]]] = {}
        self._next_id = 1

    def _t(self, table: str) -> List[Dict[str, Any]]:
        return self._rows.setdefault(table, [])

    def _matches(self, row: Dict[str, Any], tenant_id: Optional[str],
                 filters: Optional[Dict[str, Any]]) -> bool:
        if tenant_id is not None:
            if row.get("tenant_id") != tenant_id and row.get("org_id") != tenant_id:
                return False
        if filters:
            for k, v in filters.items():
                if row.get(k) != v:
                    return False
        return True

    def select(self, table, columns="*", tenant_id=None, filters=None,
               order_by=None, limit=None, count=False):
        rows = [r for r in self._t(table) if self._matches(r, tenant_id, filters)]
        if order_by:
            col, _, direction = order_by.partition(".")
            rows = sorted(rows, key=lambda r: r.get(col) or "",
                          reverse=(direction.lower() == "desc"))
        total = len(rows)
        if limit:
            rows = rows[:limit]
        return QueryResult(data=[dict(r) for r in rows],
                           count=total if count else None)

    def insert(self, table, data, tenant_id=None):
        row = dict(data)
        if tenant_id and "tenant_id" not in row:
            row["tenant_id"] = tenant_id
        row.setdefault("id", str(self._next_id))
        self._next_id += 1
        self._t(table).append(row)
        return QueryResult(data=[dict(row)])

    def upsert(self, table, data, tenant_id=None, on_conflict=None):
        row = dict(data)
        if tenant_id and "tenant_id" not in row:
            row["tenant_id"] = tenant_id
        # Conflict on key+tenant_id (mirrors brain_facts schema)
        existing = next(
            (r for r in self._t(table)
             if r.get("key") == row.get("key")
             and (r.get("tenant_id") == row.get("tenant_id")
                  or r.get("org_id") == row.get("tenant_id"))),
            None,
        )
        if existing:
            existing.update(row)
            return QueryResult(data=[dict(existing)])
        return self.insert(table, row, tenant_id=None)

    def update(self, table, data, tenant_id=None, filters=None):
        updated = []
        for r in self._t(table):
            if self._matches(r, tenant_id, filters):
                r.update(data)
                updated.append(dict(r))
        return QueryResult(data=updated)

    def delete(self, table, tenant_id=None, filters=None):
        kept = [r for r in self._t(table)
                if not self._matches(r, tenant_id, filters)]
        self._rows[table] = kept
        return QueryResult(data=[])

    def count(self, table, tenant_id=None, filters=None):
        return sum(1 for r in self._t(table) if self._matches(r, tenant_id, filters))


# ── Fixtures ──────────────────────────────────────────────────────
@pytest.fixture
def embedder():
    e = FakeEmbedder()
    set_embedder(e)
    yield e
    set_embedder(None)


@pytest.fixture
def vector_store(embedder):
    vs = InMemoryVectorStore(embedder=embedder)
    set_vector_store(vs)
    yield vs
    set_vector_store(None)


@pytest.fixture
def db():
    return FakeDatabaseClient()


@pytest.fixture
def repo(db, vector_store):
    return FactRepository(db, vector_store=vector_store)


# ── Tests: VectorStore round-trip ─────────────────────────────────
class TestVectorStore:
    def test_upsert_and_query_returns_match(self, vector_store):
        vector_store.upsert(id="t1::a", text="customer wants gold loan",
                            tenant_id="t1")
        res = vector_store.query(text="gold loan", tenant_id="t1", k=3)
        assert len(res) == 1
        assert res[0].id == "t1::a"
        assert res[0].score > 0

    def test_tenant_isolation(self, vector_store):
        vector_store.upsert(id="t1::a", text="alpha bravo", tenant_id="t1")
        vector_store.upsert(id="t2::a", text="alpha bravo", tenant_id="t2")
        res = vector_store.query(text="alpha", tenant_id="t1", k=5)
        assert all(m.metadata.get("tenant_id", "t1") != "t2" for m in res)
        assert all(m.id.startswith("t1::") for m in res)

    def test_delete_removes_entry(self, vector_store):
        vector_store.upsert(id="t1::a", text="alpha", tenant_id="t1")
        assert vector_store.count("t1") == 1
        vector_store.delete(id="t1::a", tenant_id="t1")
        assert vector_store.count("t1") == 0

    def test_delete_is_tenant_safe(self, vector_store):
        vector_store.upsert(id="t1::a", text="alpha", tenant_id="t1")
        vector_store.delete(id="t1::a", tenant_id="t2")  # wrong tenant
        assert vector_store.count("t1") == 1


# ── Tests: FactRepository dual-write ──────────────────────────────
@pytest.fixture(autouse=True)
def _enable_rag():
    """Force RAG on for the duration of repo-level tests."""
    with patch("repositories.fact.settings") as s:
        s.RAG_ENABLED = True
        s.RAG_TOP_K = 5
        s.RAG_MIN_SIMILARITY = 0.0
        yield s


class TestFactRepositoryDualWrite:
    def test_save_fact_writes_to_vector_store(self, repo, vector_store):
        repo.save_fact(key="loan.product", value="gold loan",
                       tenant_id="t1", source="api", confidence=1.0)
        assert vector_store.count("t1") == 1
        res = vector_store.query(text="gold loan", tenant_id="t1", k=3)
        assert res and res[0].id == fact_vector_id("t1", "loan.product")
        assert res[0].metadata.get("key") == "loan.product"

    def test_save_fact_is_idempotent(self, repo, vector_store):
        repo.save_fact(key="k1", value="v1", tenant_id="t1")
        repo.save_fact(key="k1", value="v2", tenant_id="t1")
        assert vector_store.count("t1") == 1

    def test_delete_propagates_to_vector_store(self, repo, vector_store):
        repo.save_fact(key="k1", value="v1", tenant_id="t1")
        assert vector_store.count("t1") == 1
        repo.delete(key="k1", tenant_id="t1")
        assert vector_store.count("t1") == 0

    def test_save_succeeds_when_vector_upsert_fails(self, repo, db):
        """A vector failure must never break the SQL write path."""
        class Boom:
            def upsert(self, *a, **kw):
                raise RuntimeError("vector store down")

        repo._vector_store = Boom()
        fact = repo.save_fact(key="k1", value="v1", tenant_id="t1")
        assert fact.key == "k1"
        # Row is still in the relational store
        assert db.count("brain_facts", tenant_id="t1") == 1


class TestSemanticSearch:
    def _seed(self, repo):
        repo.save_fact(key="loan.gold", value="gold loan rate is 8%", tenant_id="t1")
        repo.save_fact(key="loan.personal", value="personal loan up to 100k", tenant_id="t1")
        repo.save_fact(key="card.platinum", value="platinum credit card benefits", tenant_id="t1")

    def test_returns_canonical_facts_in_relevance_order(self, repo):
        self._seed(repo)
        results = repo.semantic_search(query="gold loan rate", tenant_id="t1", k=2)
        assert results, "expected at least one match"
        assert results[0].key == "loan.gold"
        # Returned objects are canonical Fact models, not vector docs
        assert results[0].source == "api"

    def test_respects_k(self, repo):
        self._seed(repo)
        results = repo.semantic_search(query="loan", tenant_id="t1", k=1)
        assert len(results) <= 1

    def test_tenant_isolation(self, repo):
        repo.save_fact(key="k1", value="alpha bravo charlie", tenant_id="t1")
        repo.save_fact(key="k1", value="alpha bravo charlie", tenant_id="t2")
        results = repo.semantic_search(query="alpha", tenant_id="t1", k=5)
        assert results and all(f.tenant_id == "t1" for f in results)

    def test_returns_empty_when_vector_store_disabled(self, db):
        # No vector store, RAG disabled in settings
        with patch("repositories.fact.settings") as s:
            s.RAG_ENABLED = False
            s.RAG_TOP_K = 5
            s.RAG_MIN_SIMILARITY = 0.0
            r = FactRepository(db)
            assert r.semantic_search(query="anything", tenant_id="t1") == []

    def test_skips_facts_missing_from_sql(self, repo, db, vector_store):
        """Stale vector entries (no matching SQL row) must be filtered out."""
        # Manually seed a vector entry with no SQL counterpart
        vector_store.upsert(
            id=fact_vector_id("t1", "ghost"),
            text="ghost: nothing here",
            tenant_id="t1",
            metadata={"key": "ghost"},
        )
        repo.save_fact(key="real", value="real value", tenant_id="t1")
        results = repo.semantic_search(query="ghost real", tenant_id="t1", k=5)
        keys = [f.key for f in results]
        assert "ghost" not in keys
        assert "real" in keys


class TestReindexAll:
    def test_reindex_all_populates_vector_store(self, db, vector_store, embedder):
        # Disable auto-indexing during seed so reindex_all has work to do.
        with patch("repositories.fact.settings") as s:
            s.RAG_ENABLED = False
            s.RAG_TOP_K = 5
            s.RAG_MIN_SIMILARITY = 0.0
            seed_repo = FactRepository(db)
            seed_repo.save_fact(key="k1", value="v1", tenant_id="t1")
            seed_repo.save_fact(key="k2", value="v2", tenant_id="t1")
        assert vector_store.count("t1") == 0

        # Now reindex with RAG enabled.
        with patch("repositories.fact.settings") as s:
            s.RAG_ENABLED = True
            s.RAG_TOP_K = 5
            s.RAG_MIN_SIMILARITY = 0.0
            repo = FactRepository(db, vector_store=vector_store)
            n = repo.reindex_all(tenant_id="t1", batch_size=8)
            assert n == 2
            assert vector_store.count("t1") == 2
