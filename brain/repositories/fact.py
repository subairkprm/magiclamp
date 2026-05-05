"""
FactRepository - Repository pattern for Fact entity operations.
Provides clean interface between database and API for brain facts storage and retrieval.

When ``settings.RAG_ENABLED`` is true, ``save_fact`` and ``delete`` also
maintain an embedding entry in the configured :class:`VectorStore`, and a new
:meth:`semantic_search` method is available that performs vector retrieval and
joins the matched ids back to the canonical SQL records.
"""

from typing import Optional, List, Dict, Any
from core.config import settings
from core.database import DatabaseClient, QueryResult
from core.models import Fact
from core.exceptions import RecordNotFoundError, DatabaseError
from core.logger import get_logger
from core.vector_store import VectorStore, get_vector_store, fact_vector_id

log = get_logger("repositories.fact")


def _fact_to_text(key: str, value: Any) -> str:
    """Render a fact (key, value) into the document text used for embedding."""
    return f"{key}: {value}"


class FactRepository:
    """Repository for Fact entity operations with multi-tenant support."""

    def __init__(self, db_client: DatabaseClient, vector_store: Optional[VectorStore] = None):
        """
        Initialize FactRepository with a DatabaseClient.

        Args:
            db_client: DatabaseClient instance for database operations
            vector_store: Optional VectorStore for semantic search. If omitted
                and ``settings.RAG_ENABLED`` is true, the global singleton is
                used lazily on first need.
        """
        self.db = db_client
        self.table = "brain_facts"
        self._vector_store = vector_store

    # ── Vector store helpers ──────────────────────────────────────
    def _vs(self) -> Optional[VectorStore]:
        """Return the vector store if RAG is enabled (or if explicitly injected)."""
        if self._vector_store is not None:
            return self._vector_store
        if not settings.RAG_ENABLED:
            return None
        try:
            self._vector_store = get_vector_store()
            return self._vector_store
        except Exception as e:
            log.warning(f"Vector store unavailable: {e}")
            return None

    def _index_fact(self, key: str, value: Any, tenant_id: str,
                    source: str, confidence: float) -> None:
        """Best-effort upsert of a fact into the vector store. Never raises."""
        vs = self._vs()
        if vs is None:
            return
        try:
            vs.upsert(
                id=fact_vector_id(tenant_id, key),
                text=_fact_to_text(key, value),
                tenant_id=tenant_id,
                metadata={"key": key, "source": source, "confidence": float(confidence)},
            )
        except Exception as e:
            # Dual-write must never break the relational write path.
            log.warning(f"Vector upsert failed for fact '{key}' (tenant={tenant_id}): {e}")

    def _unindex_fact(self, key: str, tenant_id: str) -> None:
        """Best-effort delete of a fact from the vector store. Never raises."""
        vs = self._vs()
        if vs is None:
            return
        try:
            vs.delete(id=fact_vector_id(tenant_id, key), tenant_id=tenant_id)
        except Exception as e:
            log.warning(f"Vector delete failed for fact '{key}' (tenant={tenant_id}): {e}")


    def get_recent_facts(self, tenant_id: str, limit: int = 20, order_by: str = "created_at.desc") -> List[Fact]:
        """
        Get recent facts for a tenant.

        Args:
            tenant_id: Tenant identifier for data isolation
            limit: Maximum number of facts to return (default: 20)
            order_by: Order clause (default: "created_at.desc")

        Returns:
            List of Fact models ordered by the specified field

        Raises:
            DatabaseError: If database query fails
        """
        try:
            result: QueryResult = self.db.select(
                table=self.table, columns="*", tenant_id=tenant_id, order_by=order_by, limit=limit
            )

            if not result.success:
                raise DatabaseError(f"Failed to query recent facts: {result.error}")

            facts = [Fact(**fact_data) for fact_data in result.data]
            log.debug(f"Retrieved {len(facts)} recent facts for tenant {tenant_id}")
            return facts

        except Exception as e:
            log.error(f"Error getting recent facts: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error retrieving recent facts: {str(e)}")

    def save_fact(self, key: str, value: Any, tenant_id: str, source: str = "api", confidence: float = 1.0) -> Fact:
        """
        Save (upsert) a fact for a tenant.

        Args:
            key: Fact key (must be lowercase alphanumeric with dots, underscores, dashes)
            value: Fact value (can be any JSON-serializable type)
            tenant_id: Tenant identifier for data isolation
            source: Source of the fact (default: "api")
            confidence: Confidence score 0.0-1.0 (default: 1.0)

        Returns:
            Saved Fact model

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            fact_data = {
                "key": key,
                "value": value,
                "source": source,
                "confidence": confidence,
            }

            # Use upsert to handle both insert and update cases
            result: QueryResult = self.db.upsert(
                table=self.table, data=fact_data, tenant_id=tenant_id, on_conflict="key,tenant_id"
            )

            if not result.success:
                raise DatabaseError(f"Failed to save fact: {result.error}")

            if not result.data:
                raise DatabaseError("Fact saved but no data returned")

            log.info(f"Saved fact '{key}' for tenant {tenant_id}")
            saved = Fact(**result.data[0])
            # Dual-write to vector store (best-effort, never raises)
            self._index_fact(key=key, value=value, tenant_id=tenant_id,
                             source=source, confidence=confidence)
            return saved

        except Exception as e:
            log.error(f"Error saving fact {key}: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error saving fact: {str(e)}")

    def get_by_key(self, key: str, tenant_id: str) -> Optional[Fact]:
        """
        Get a fact by its key within a tenant.

        Args:
            key: Fact key to look up
            tenant_id: Tenant identifier for data isolation

        Returns:
            Fact model if found, None otherwise

        Raises:
            DatabaseError: If database query fails
        """
        try:
            result: QueryResult = self.db.select(
                table=self.table, columns="*", tenant_id=tenant_id, filters={"key": key}, limit=1
            )

            if not result.success:
                raise DatabaseError(f"Failed to query fact by key: {result.error}")

            if result.data:
                return Fact(**result.data[0])
            return None

        except Exception as e:
            log.error(f"Error getting fact by key {key}: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error retrieving fact by key: {str(e)}")

    def get_all(
        self, tenant_id: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Fact]:
        """
        Get all facts for a tenant with optional filtering.

        Args:
            tenant_id: Tenant identifier for data isolation
            limit: Maximum number of facts to return (optional)
            filters: Additional filters to apply (optional)

        Returns:
            List of Fact models

        Raises:
            DatabaseError: If database query fails
        """
        try:
            result: QueryResult = self.db.select(
                table=self.table,
                columns="*",
                tenant_id=tenant_id,
                filters=filters,
                order_by="created_at.desc",
                limit=limit,
            )

            if not result.success:
                raise DatabaseError(f"Failed to query facts: {result.error}")

            return [Fact(**fact_data) for fact_data in result.data]

        except Exception as e:
            log.error(f"Error getting all facts: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error retrieving facts: {str(e)}")

    def get_by_source(self, source: str, tenant_id: str, limit: Optional[int] = None) -> List[Fact]:
        """
        Get facts by source within a tenant.

        Args:
            source: Source identifier to filter by
            tenant_id: Tenant identifier for data isolation
            limit: Maximum number of facts to return (optional)

        Returns:
            List of Fact models from the specified source

        Raises:
            DatabaseError: If database query fails
        """
        try:
            result: QueryResult = self.db.select(
                table=self.table,
                columns="*",
                tenant_id=tenant_id,
                filters={"source": source},
                order_by="created_at.desc",
                limit=limit,
            )

            if not result.success:
                raise DatabaseError(f"Failed to query facts by source: {result.error}")

            return [Fact(**fact_data) for fact_data in result.data]

        except Exception as e:
            log.error(f"Error getting facts by source {source}: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error retrieving facts by source: {str(e)}")

    def count(self, tenant_id: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count facts for a tenant with optional filtering.

        Args:
            tenant_id: Tenant identifier for data isolation
            filters: Additional filters to apply (optional)

        Returns:
            Count of matching facts

        Raises:
            DatabaseError: If database query fails
        """
        try:
            count = self.db.count(table=self.table, tenant_id=tenant_id, filters=filters)
            return count

        except Exception as e:
            log.error(f"Error counting facts: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error counting facts: {str(e)}")

    def delete(self, key: str, tenant_id: str) -> bool:
        """
        Delete a fact by key from a tenant.

        Args:
            key: Fact key to delete
            tenant_id: Tenant identifier for data isolation

        Returns:
            True if fact was deleted

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result: QueryResult = self.db.delete(table=self.table, tenant_id=tenant_id, filters={"key": key})

            if not result.success:
                raise DatabaseError(f"Failed to delete fact: {result.error}")

            log.info(f"Deleted fact '{key}' from tenant {tenant_id}")
            # Mirror the delete into the vector store (best-effort)
            self._unindex_fact(key=key, tenant_id=tenant_id)
            return True

        except Exception as e:
            log.error(f"Error deleting fact {key}: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error deleting fact: {str(e)}")

    def search_by_confidence(
        self, tenant_id: str, min_confidence: float = 0.0, max_confidence: float = 1.0, limit: Optional[int] = None
    ) -> List[Fact]:
        """
        Get facts within a confidence range.

        Note: This is a basic implementation. For more complex filtering,
        consider extending DatabaseClient with range query support.

        Args:
            tenant_id: Tenant identifier for data isolation
            min_confidence: Minimum confidence score (default: 0.0)
            max_confidence: Maximum confidence score (default: 1.0)
            limit: Maximum number of facts to return (optional)

        Returns:
            List of Fact models within the confidence range

        Raises:
            DatabaseError: If database query fails
        """
        try:
            # Get all facts and filter by confidence
            # Note: This could be optimized with database-level filtering
            result: QueryResult = self.db.select(
                table=self.table, columns="*", tenant_id=tenant_id, order_by="confidence.desc", limit=limit
            )

            if not result.success:
                raise DatabaseError(f"Failed to query facts: {result.error}")

            # Filter by confidence range
            facts = [
                Fact(**fact_data)
                for fact_data in result.data
                if min_confidence <= fact_data.get("confidence", 1.0) <= max_confidence
            ]

            return facts

        except Exception as e:
            log.error(f"Error searching facts by confidence: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error searching facts by confidence: {str(e)}")


    # ── RAG: semantic retrieval ───────────────────────────────────
    def semantic_search(
        self,
        query: str,
        tenant_id: str,
        k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[Fact]:
        """Retrieve facts most semantically relevant to ``query``.

        The vector store returns candidate ids; this method then fetches the
        canonical rows from the relational store keyed by ``(tenant_id, key)``
        so callers always see fresh, authoritative data (not stale embedded
        copies). Results are returned in the order of vector relevance.

        Returns an empty list when the vector store is unavailable or RAG is
        disabled — callers should fall back to a non-RAG path in that case.
        """
        vs = self._vs()
        if vs is None:
            return []

        top_k = k if k is not None else settings.RAG_TOP_K
        threshold = min_score if min_score is not None else settings.RAG_MIN_SIMILARITY

        try:
            matches = vs.query(text=query, tenant_id=tenant_id, k=top_k, min_score=threshold)
        except Exception as e:
            log.warning(f"Vector search failed (tenant={tenant_id}): {e}")
            return []

        if not matches:
            return []

        # Pull the keys out of vector ids and fetch canonical rows.
        keys_in_order: List[str] = []
        for m in matches:
            key = (m.metadata or {}).get("key")
            if not key:
                # id is "<tenant_id>::<key>"
                key = m.id.split("::", 1)[1] if "::" in m.id else m.id
            keys_in_order.append(key)

        # Bulk fetch from relational store, then reorder by vector relevance.
        facts_by_key: Dict[str, Fact] = {}
        for key in keys_in_order:
            try:
                fact = self.get_by_key(key=key, tenant_id=tenant_id)
            except Exception as e:
                log.debug(f"semantic_search: failed to fetch fact '{key}': {e}")
                fact = None
            if fact is not None:
                facts_by_key[key] = fact

        return [facts_by_key[k] for k in keys_in_order if k in facts_by_key]

    def reindex_all(self, tenant_id: str, batch_size: int = 64) -> int:
        """Re-embed every fact for ``tenant_id`` into the vector store.

        Used by the backfill script; idempotent because vector ids are derived
        from ``(tenant_id, key)``. Returns the number of facts indexed.
        """
        vs = self._vs()
        if vs is None:
            log.warning("reindex_all called but vector store is unavailable")
            return 0

        facts = self.get_all(tenant_id=tenant_id)
        total = 0
        batch: List[Dict[str, Any]] = []
        for f in facts:
            batch.append({
                "id": fact_vector_id(tenant_id, f.key),
                "text": _fact_to_text(f.key, f.value),
                "tenant_id": tenant_id,
                "metadata": {
                    "key": f.key,
                    "source": f.source,
                    "confidence": float(f.confidence),
                },
            })
            if len(batch) >= batch_size:
                vs.upsert_batch(batch)
                total += len(batch)
                batch = []
        if batch:
            vs.upsert_batch(batch)
            total += len(batch)
        log.info(f"Reindexed {total} facts for tenant {tenant_id}")
        return total
