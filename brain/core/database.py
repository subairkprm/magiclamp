"""
MagicLamp Database Abstraction Layer
Provides database-agnostic interface with multi-tenant support.
Completely removes hardcoded Supabase dependencies from API routes.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type, TypeVar
from datetime import datetime
from core.config import settings
from core.logger import get_logger
from core.models import TenantModel

log = get_logger("database")

T = TypeVar("T", bound=TenantModel)


class QueryResult:
    """Standardized query result wrapper."""

    def __init__(self, data: List[Dict[str, Any]], count: Optional[int] = None, error: Optional[str] = None):
        self.data = data
        self.count = count if count is not None else len(data)
        self.error = error
        self.success = error is None

    def __bool__(self):
        return self.success and len(self.data) > 0


class DatabaseClient(ABC):
    """Abstract base class for database operations with multi-tenant support."""

    @abstractmethod
    def select(
        self,
        table: str,
        columns: str = "*",
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        count: bool = False,
    ) -> QueryResult:
        """
        Select records from a table.

        Args:
            table: Table name
            columns: Columns to select (default: "*")
            tenant_id: Tenant ID for automatic filtering (multi-tenant isolation)
            filters: Additional filters as dict {column: value}
            order_by: Order by clause (e.g., "created_at.desc")
            limit: Maximum number of records to return
            count: Whether to include total count

        Returns:
            QueryResult with data and optional count
        """
        pass

    @abstractmethod
    def insert(self, table: str, data: Dict[str, Any], tenant_id: Optional[str] = None) -> QueryResult:
        """
        Insert a record into a table.

        Args:
            table: Table name
            data: Data to insert
            tenant_id: Tenant ID (auto-added to data if provided)

        Returns:
            QueryResult with inserted record
        """
        pass

    @abstractmethod
    def upsert(
        self, table: str, data: Dict[str, Any], tenant_id: Optional[str] = None, on_conflict: Optional[str] = None
    ) -> QueryResult:
        """
        Upsert (insert or update) a record.

        Args:
            table: Table name
            data: Data to upsert
            tenant_id: Tenant ID (auto-added to data if provided)
            on_conflict: Conflict resolution columns

        Returns:
            QueryResult with upserted record
        """
        pass

    @abstractmethod
    def update(
        self,
        table: str,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """
        Update records in a table.

        Args:
            table: Table name
            data: Data to update
            tenant_id: Tenant ID for filtering
            filters: Additional filters for which records to update

        Returns:
            QueryResult with updated records
        """
        pass

    @abstractmethod
    def delete(
        self, table: str, tenant_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Delete records from a table.

        Args:
            table: Table name
            tenant_id: Tenant ID for filtering
            filters: Additional filters for which records to delete

        Returns:
            QueryResult (empty data on success)
        """
        pass

    @abstractmethod
    def count(self, table: str, tenant_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in a table.

        Args:
            table: Table name
            tenant_id: Tenant ID for filtering
            filters: Additional filters

        Returns:
            Count of matching records
        """
        pass


class SupabaseClient(DatabaseClient):
    """Concrete Supabase implementation of DatabaseClient."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize Supabase client.

        Args:
            url: Supabase URL (defaults to settings.SUPABASE_URL)
            key: Supabase key (defaults to settings.SUPABASE_KEY)
        """
        # Lazy import — supabase is only required when DB_BACKEND=supabase, so
        # importing it eagerly would force every deployment (including SQLite-
        # only Railway deploys) to ship the dependency.
        from supabase import create_client, Client  # noqa: F401

        self.url = url or settings.SUPABASE_URL
        self.key = key or settings.SUPABASE_KEY
        if not self.url or not self.key:
            raise ValueError(
                "SupabaseClient requires SUPABASE_URL and SUPABASE_SERVICE_KEY"
            )
        self.client = create_client(self.url, self.key)
        log.info("Supabase client initialized")

    def _add_tenant_filter(self, query, tenant_id: Optional[str]):
        """Add tenant_id filter to query if provided."""
        if tenant_id:
            # Support both tenant_id and org_id for backwards compatibility
            query = query.eq("tenant_id", tenant_id).or_(f"org_id.eq.{tenant_id}")
        return query

    def _inject_tenant_id(self, data: Dict[str, Any], tenant_id: Optional[str]) -> Dict[str, Any]:
        """Inject tenant_id into data if provided and not already present."""
        if tenant_id and "tenant_id" not in data and "org_id" not in data:
            data = {**data, "tenant_id": tenant_id}
        return data

    def select(
        self,
        table: str,
        columns: str = "*",
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        count: bool = False,
    ) -> QueryResult:
        """Select records from Supabase table."""
        try:
            # Build query
            count_option = "exact" if count else None
            query = self.client.table(table).select(columns, count=count_option)

            # Apply tenant filter
            query = self._add_tenant_filter(query, tenant_id)

            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Apply ordering
            if order_by:
                # Parse order_by like "created_at.desc" or "name.asc"
                parts = order_by.split(".")
                column = parts[0]
                desc = len(parts) > 1 and parts[1].lower() == "desc"
                query = query.order(column, desc=desc)

            # Apply limit
            if limit:
                query = query.limit(limit)

            # Execute
            response = query.execute()
            return QueryResult(data=response.data or [], count=response.count if count else None)

        except Exception as e:
            log.error(f"Supabase select error on {table}: {str(e)}")
            return QueryResult(data=[], error=str(e))

    def insert(self, table: str, data: Dict[str, Any], tenant_id: Optional[str] = None) -> QueryResult:
        """Insert record into Supabase table."""
        try:
            # Inject tenant_id
            data = self._inject_tenant_id(data, tenant_id)

            # Execute
            response = self.client.table(table).insert(data).execute()
            return QueryResult(data=response.data or [])

        except Exception as e:
            log.error(f"Supabase insert error on {table}: {str(e)}")
            return QueryResult(data=[], error=str(e))

    def upsert(
        self, table: str, data: Dict[str, Any], tenant_id: Optional[str] = None, on_conflict: Optional[str] = None
    ) -> QueryResult:
        """Upsert record in Supabase table."""
        try:
            # Inject tenant_id
            data = self._inject_tenant_id(data, tenant_id)

            # Execute
            query = self.client.table(table).upsert(data)
            if on_conflict:
                query = query.on_conflict(on_conflict)

            response = query.execute()
            return QueryResult(data=response.data or [])

        except Exception as e:
            log.error(f"Supabase upsert error on {table}: {str(e)}")
            return QueryResult(data=[], error=str(e))

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """Update records in Supabase table."""
        try:
            query = self.client.table(table).update(data)

            # Apply tenant filter
            query = self._add_tenant_filter(query, tenant_id)

            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Execute
            response = query.execute()
            return QueryResult(data=response.data or [])

        except Exception as e:
            log.error(f"Supabase update error on {table}: {str(e)}")
            return QueryResult(data=[], error=str(e))

    def delete(
        self, table: str, tenant_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Delete records from Supabase table."""
        try:
            query = self.client.table(table).delete()

            # Apply tenant filter
            query = self._add_tenant_filter(query, tenant_id)

            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Execute
            response = query.execute()
            return QueryResult(data=[])

        except Exception as e:
            log.error(f"Supabase delete error on {table}: {str(e)}")
            return QueryResult(data=[], error=str(e))

    def count(self, table: str, tenant_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in Supabase table."""
        result = self.select(table=table, columns="id", tenant_id=tenant_id, filters=filters, count=True)
        return result.count or 0

    def get_raw_client(self):
        """
        Get the raw Supabase client for advanced operations.
        Use sparingly - prefer using abstracted methods.
        """
        return self.client


# ── GLOBAL DATABASE CLIENT ────────────────────────
# Singleton instance for dependency injection
_db_client: Optional[DatabaseClient] = None


def get_database_client() -> DatabaseClient:
    """
    Get the global database client instance.

    Selects the implementation based on ``settings.DB_BACKEND``:
      * ``sqlite`` (default) — local file at ``${DATA_DIR}/magiclamp.db``;
        no external service required. Ideal for Railway / single-box deploys.
      * ``supabase`` — managed Postgres via Supabase; requires
        ``SUPABASE_URL`` + ``SUPABASE_SERVICE_KEY``.
    """
    global _db_client
    if _db_client is None:
        backend = (settings.DB_BACKEND or "sqlite").lower()
        if backend == "supabase":
            _db_client = SupabaseClient()
        elif backend == "sqlite":
            from core.database_sqlite import SQLiteClient

            _db_client = SQLiteClient()
        else:
            raise ValueError(
                f"Unknown DB_BACKEND={backend!r}. Supported: 'sqlite', 'supabase'."
            )
    return _db_client


def set_database_client(client: DatabaseClient):
    """
    Set a custom database client (useful for testing or swapping implementations).
    """
    global _db_client
    _db_client = client
