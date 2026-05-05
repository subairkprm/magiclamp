"""
MagicLamp Vector Store Abstraction

Mirrors the :class:`core.database.DatabaseClient` pattern but for dense-vector
search. Concrete implementations:

* :class:`ChromaVectorStore` — persistent ChromaDB at ``settings.VECTOR_STORE_PATH``
  (defaults to ``{DATA_DIR}/chroma``). A single collection is used; tenant
  isolation is enforced via the ``tenant_id`` metadata filter.
* :class:`InMemoryVectorStore` — pure-Python fallback used when chromadb is
  unavailable and a default for tests. Cosine similarity over normalized vectors.

The chosen implementation is selected by ``settings.VECTOR_STORE``.
Repositories obtain the store via :func:`get_vector_store`; tests can swap it
via :func:`set_vector_store`.

A vector-store ``id`` for a fact is deterministically derived from
``(tenant_id, key)`` so dual-writes are idempotent and ``delete`` is exact.
"""

from __future__ import annotations

import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional

from core.config import settings
from core.embedder import Embedder, get_embedder
from core.logger import get_logger

log = get_logger("vector_store")


def fact_vector_id(tenant_id: str, key: str) -> str:
    """Stable id used for vector-store entries representing a fact."""
    return f"{tenant_id}::{key}"


@dataclass
class VectorMatch:
    """A single search result returned by a :class:`VectorStore`."""

    id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    document: Optional[str] = None


class VectorStore(ABC):
    """Abstract dense-vector store with tenant-aware operations."""

    @abstractmethod
    def upsert(
        self,
        id: str,
        text: str,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> None: ...

    def upsert_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> None:
        """Default impl loops; override for true batching.

        Each item is ``{"id", "text", "tenant_id", "metadata"?, "embedding"?}``.
        """
        for it in items:
            self.upsert(
                id=it["id"],
                text=it["text"],
                tenant_id=it["tenant_id"],
                metadata=it.get("metadata"),
                embedding=it.get("embedding"),
            )

    @abstractmethod
    def query(
        self,
        text: str,
        tenant_id: str,
        k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorMatch]: ...

    @abstractmethod
    def delete(self, id: str, tenant_id: str) -> None: ...

    @abstractmethod
    def count(self, tenant_id: Optional[str] = None) -> int: ...


# ── IN-MEMORY (fallback / tests) ──────────────────────────────────
class InMemoryVectorStore(VectorStore):
    """Simple in-process vector store backed by a Python dict.

    Cosine similarity is computed directly. Embeddings are expected to be
    L2-normalized (which both :class:`LocalEmbedder` and the in-memory
    fallback produce), so cosine similarity reduces to a dot product.
    """

    def __init__(self, embedder: Optional[Embedder] = None):
        self._embedder = embedder
        self._data: Dict[str, Dict[str, Any]] = {}

    def _embed(self, text: str) -> List[float]:
        emb = self._embedder or get_embedder()
        return emb.embed(text)

    def upsert(self, id, text, tenant_id, metadata=None, embedding=None):
        vec = embedding if embedding is not None else self._embed(text)
        self._data[id] = {
            "tenant_id": tenant_id,
            "metadata": dict(metadata or {}),
            "document": text,
            "vec": vec,
        }

    def query(self, text, tenant_id, k=5, min_score=0.0, filters=None):
        q = self._embed(text)
        results: List[VectorMatch] = []
        for vid, row in self._data.items():
            if row["tenant_id"] != tenant_id:
                continue
            if filters:
                meta = row["metadata"]
                if any(meta.get(fk) != fv for fk, fv in filters.items()):
                    continue
            score = _dot(q, row["vec"])
            if score < min_score:
                continue
            results.append(
                VectorMatch(
                    id=vid,
                    score=float(score),
                    metadata=dict(row["metadata"]),
                    document=row["document"],
                )
            )
        results.sort(key=lambda m: m.score, reverse=True)
        return results[:k]

    def delete(self, id, tenant_id):
        row = self._data.get(id)
        if row is not None and row["tenant_id"] == tenant_id:
            self._data.pop(id, None)

    def count(self, tenant_id=None):
        if tenant_id is None:
            return len(self._data)
        return sum(1 for row in self._data.values() if row["tenant_id"] == tenant_id)


def _dot(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    s = 0.0
    for i in range(n):
        s += a[i] * b[i]
    # Defensive normalize if not already unit length.
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return s / (na * nb)


# ── CHROMA ────────────────────────────────────────────────────────
class ChromaVectorStore(VectorStore):
    """Persistent ChromaDB-backed vector store.

    A single collection is used for all tenants; isolation is enforced by
    ``where={"tenant_id": ...}`` clauses on every read/write/delete.
    """

    def __init__(self, path: Optional[str] = None, collection: Optional[str] = None,
                 embedder: Optional[Embedder] = None):
        # Lazy import so test environments without chromadb still work.
        import chromadb  # type: ignore

        path = path or settings.VECTOR_STORE_PATH or os.path.join(settings.DATA_DIR, "chroma")
        os.makedirs(path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=path)
        # We supply our own embeddings (via the Embedder layer) so chromadb
        # never tries to download a model at import time.
        self._collection = self._client.get_or_create_collection(
            name=collection or settings.VECTOR_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = embedder
        log.info(f"ChromaVectorStore initialized at {path}")

    def _embed(self, text: str) -> List[float]:
        emb = self._embedder or get_embedder()
        return emb.embed(text)

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        emb = self._embedder or get_embedder()
        return emb.embed_batch(texts)

    def upsert(self, id, text, tenant_id, metadata=None, embedding=None):
        meta = {"tenant_id": tenant_id, **(metadata or {})}
        vec = embedding if embedding is not None else self._embed(text)
        self._collection.upsert(
            ids=[id], documents=[text], metadatas=[meta], embeddings=[vec]
        )

    def upsert_batch(self, items):
        if not items:
            return
        ids = [it["id"] for it in items]
        docs = [it["text"] for it in items]
        metas = [{"tenant_id": it["tenant_id"], **(it.get("metadata") or {})} for it in items]
        vecs = [it.get("embedding") for it in items]
        # Embed in batch any items missing precomputed embeddings.
        missing_idx = [i for i, v in enumerate(vecs) if v is None]
        if missing_idx:
            new_vecs = self._embed_batch([docs[i] for i in missing_idx])
            for i, v in zip(missing_idx, new_vecs):
                vecs[i] = v
        self._collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=vecs)

    def query(self, text, tenant_id, k=5, min_score=0.0, filters=None):
        where: Dict[str, Any] = {"tenant_id": tenant_id}
        if filters:
            where.update(filters)
        vec = self._embed(text)
        res = self._collection.query(
            query_embeddings=[vec], n_results=k, where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: List[VectorMatch] = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for i, vid in enumerate(ids):
            # chromadb cosine "distance" is 1 - cosine_similarity
            dist = float(dists[i]) if i < len(dists) and dists[i] is not None else 1.0
            score = 1.0 - dist
            if score < min_score:
                continue
            out.append(VectorMatch(
                id=vid,
                score=score,
                metadata=dict(metas[i]) if i < len(metas) and metas[i] else {},
                document=docs[i] if i < len(docs) else None,
            ))
        return out

    def delete(self, id, tenant_id):
        # Tenant filter ensures cross-tenant deletes are impossible.
        self._collection.delete(ids=[id], where={"tenant_id": tenant_id})

    def count(self, tenant_id=None):
        if tenant_id is None:
            return self._collection.count()
        # Chroma has no native filtered count; use get() with metadata filter.
        res = self._collection.get(where={"tenant_id": tenant_id}, include=[])
        return len(res.get("ids") or [])


# ── SINGLETON ─────────────────────────────────────────────────────
_store: Optional[VectorStore] = None
_store_lock = Lock()


def _build_vector_store() -> VectorStore:
    backend = (settings.VECTOR_STORE or "chroma").lower()
    if backend == "memory":
        log.info("Using InMemoryVectorStore")
        return InMemoryVectorStore()
    if backend == "chroma":
        try:
            return ChromaVectorStore()
        except Exception as e:
            log.error(f"Failed to init ChromaVectorStore ({e}); falling back to InMemoryVectorStore")
            return InMemoryVectorStore()
    log.warning(f"Unknown VECTOR_STORE '{backend}'; using InMemoryVectorStore")
    return InMemoryVectorStore()


def get_vector_store() -> VectorStore:
    """Return the process-wide :class:`VectorStore` singleton."""
    global _store
    if _store is not None:
        return _store
    with _store_lock:
        if _store is None:
            _store = _build_vector_store()
    return _store


def set_vector_store(store: Optional[VectorStore]) -> None:
    """Override the vector store singleton (primarily for tests)."""
    global _store
    _store = store
