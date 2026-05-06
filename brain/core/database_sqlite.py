"""
SQLite implementation of :class:`DatabaseClient`.

This is the **default** backend for MagicLamp deployments — it requires no
external services and stores everything in a single file under ``DATA_DIR``
(typically a Railway / Docker volume). It honours the same multi-tenant
contract as :class:`SupabaseClient`:

* ``select`` / ``update`` / ``delete`` filter by ``tenant_id`` whenever one
  is supplied (and treat ``org_id`` as an alias for backwards compatibility);
* ``insert`` / ``upsert`` inject ``tenant_id`` into the row when supplied and
  not already present;
* every method returns a :class:`QueryResult` (no exceptions surface on the
  happy path).

JSON-typed columns (``value``, ``data``, ``settings``, ``config``, ``scopes``,
``events``, ``features``, ``limits``, ``old_data``, ``new_data``,
``context``, ``metrics``) are transparently encoded/decoded so callers can
hand in plain Python dicts/lists exactly as they do with the Supabase client.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config import settings
from core.database import DatabaseClient, QueryResult
from core.logger import get_logger

log = get_logger("database.sqlite")


# Columns that should be (de)serialised as JSON. The set is conservative — we
# only round-trip values for columns we know are JSON in the existing schema.
_JSON_COLUMNS: set[str] = {
    "value",
    "data",
    "settings",
    "config",
    "scopes",
    "events",
    "features",
    "limits",
    "old_data",
    "new_data",
    "context",
    "metrics",
}

# Columns that are stored as INTEGER in SQLite but exposed as bool to callers.
_BOOL_COLUMNS: set[str] = {"is_active", "verified"}


def _schema_path() -> Path:
    """Return the absolute path to the bundled schema.sql file."""
    return Path(__file__).resolve().parent.parent / "migrations" / "schema.sql"


def _default_db_path() -> str:
    """Resolve the SQLite file path from settings.DATA_DIR."""
    data_dir = Path(settings.DATA_DIR).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "magiclamp.db")


def _encode_value(column: str, value: Any) -> Any:
    """Encode a Python value for storage in SQLite."""
    if value is None:
        return None
    if column in _JSON_COLUMNS and not isinstance(value, str):
        return json.dumps(value)
    if column in _BOOL_COLUMNS and isinstance(value, bool):
        return 1 if value else 0
    return value


def _validate_identifier(name: str, what: str) -> str:
    """Reject anything that isn't a plain SQL identifier (alnum + underscore).

    SQLite parameterised queries don't apply to table or column *names* — those
    are interpolated into the SQL string. We only ever build identifiers from
    callers' arguments (table names, column names, order_by clause), so a
    strict whitelist is the only safe approach against injection.
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"Invalid {what}: must be a non-empty string")
    # Allow letters, digits, underscore. Reject backticks, semicolons, spaces,
    # quotes, parens, anything else. Length cap protects against pathological
    # inputs.
    if len(name) > 63 or not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe {what}: {name!r}")
    return name


def _decode_row(row: sqlite3.Row) -> Dict[str, Any]:
    """Decode a sqlite3.Row into a plain dict with JSON/bool columns rehydrated."""
    out: Dict[str, Any] = {}
    for key in row.keys():
        val = row[key]
        if val is None:
            out[key] = None
            continue
        if key in _JSON_COLUMNS and isinstance(val, str):
            try:
                out[key] = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                out[key] = val
            continue
        if key in _BOOL_COLUMNS and isinstance(val, int):
            out[key] = bool(val)
            continue
        out[key] = val
    return out


class SQLiteClient(DatabaseClient):
    """File-backed SQLite implementation of :class:`DatabaseClient`."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _default_db_path()
        # SQLite connections are not safe to share across threads by default;
        # we serialise access with a lock so the same connection instance can
        # be reused. ``check_same_thread=False`` is required because FastAPI
        # may dispatch calls on different worker threads.
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # autocommit; we manage transactions explicitly
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._apply_schema()
        log.info(f"SQLite client initialised at {self.db_path}")

    # ── schema bootstrap ─────────────────────────────────────────────
    def _apply_schema(self) -> None:
        """Create tables on first startup. Idempotent (uses IF NOT EXISTS)."""
        path = _schema_path()
        if not path.exists():  # pragma: no cover - shipped with the package
            log.warning(f"SQLite schema file not found at {path}; skipping bootstrap")
            return
        with self._lock:
            self._conn.executescript(path.read_text())

    # ── helpers ──────────────────────────────────────────────────────
    def _tenant_filter_for(
        self, table: str, tenant_id: Optional[str]
    ) -> Tuple[str, List[Any]]:
        """Build the SQL fragment that scopes a query to a tenant.

        Returns ``(fragment, params)`` where ``fragment`` is empty when no
        tenant is supplied **or** when the table has neither a ``tenant_id``
        nor an ``org_id`` column. Mirrors ``SupabaseClient`` (which OR's
        tenant_id with org_id for backwards compatibility) but only includes
        each column that actually exists on the target table.
        """
        if not tenant_id:
            return "", []
        cols = self._existing_columns(table)
        clauses: List[str] = []
        params: List[Any] = []
        if "tenant_id" in cols:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if "org_id" in cols:
            clauses.append("org_id = ?")
            params.append(tenant_id)
        if not clauses:
            return "", []
        if len(clauses) == 1:
            return clauses[0], params
        return "(" + " OR ".join(clauses) + ")", params

    def _existing_columns(self, table: str) -> set[str]:
        _validate_identifier(table, "table name")
        with self._lock:
            cur = self._conn.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cur.fetchall()}

    @staticmethod
    def _validate_columns(cols: List[str], existing: set[str]) -> None:
        """Reject column names that aren't real columns on the target table.

        Catches both SQL-injection attempts (no ``;`` / spaces survive the
        identifier check) and harmless typos that would otherwise produce
        confusing errors later in the SQL pipeline.
        """
        for c in cols:
            _validate_identifier(c, "column name")
            if c not in existing:
                raise ValueError(f"Unknown column {c!r} on target table")

    def _inject_tenant_id(
        self, data: Dict[str, Any], tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        if tenant_id and "tenant_id" not in data and "org_id" not in data:
            data = {**data, "tenant_id": tenant_id}
        return data

    # ── DatabaseClient interface ─────────────────────────────────────
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
        try:
            _validate_identifier(table, "table name")
            existing = self._existing_columns(table)
            # Validate `columns` projection — only "*" or comma-separated
            # identifiers from the table are allowed (defends against
            # ``SELECT * FROM x; DROP TABLE y``).
            if columns and columns.strip() and columns.strip() != "*":
                proj = [c.strip() for c in columns.split(",") if c.strip()]
                self._validate_columns(proj, existing)
                cols = ",".join(proj)
            else:
                cols = "*"
            sql = f"SELECT {cols} FROM {table}"
            where: List[str] = []
            params: List[Any] = []

            tenant_frag, tenant_params = self._tenant_filter_for(table, tenant_id)
            if tenant_frag:
                where.append(tenant_frag)
                params.extend(tenant_params)

            if filters:
                self._validate_columns(list(filters.keys()), existing)
                for k, v in filters.items():
                    where.append(f"{k} = ?")
                    params.append(_encode_value(k, v))

            if where:
                sql += " WHERE " + " AND ".join(where)

            if order_by:
                col, _, direction = order_by.partition(".")
                col = col.strip() or "id"
                desc = direction.strip().lower() == "desc"
                # Validate identifier — only alnum / underscore allowed to
                # protect against SQL injection via the order_by string.
                if not col.replace("_", "").isalnum():
                    raise ValueError(f"Unsafe order_by column: {col!r}")
                sql += f" ORDER BY {col} {'DESC' if desc else 'ASC'}"

            if limit:
                sql += f" LIMIT {int(limit)}"

            with self._lock:
                cur = self._conn.execute(sql, params)
                rows = cur.fetchall()
            data = [_decode_row(r) for r in rows]

            total: Optional[int] = None
            if count:
                # Cheaper than rerunning the query — count(*) of the same WHERE.
                count_sql = f"SELECT COUNT(*) AS c FROM {table}"
                if where:
                    count_sql += " WHERE " + " AND ".join(where)
                with self._lock:
                    crow = self._conn.execute(count_sql, params).fetchone()
                total = int(crow["c"])
            return QueryResult(data=data, count=total)
        except Exception as e:
            log.error(f"SQLite select error on {table}: {e}")
            return QueryResult(data=[], error=str(e))

    def insert(
        self, table: str, data: Dict[str, Any], tenant_id: Optional[str] = None
    ) -> QueryResult:
        try:
            row = dict(self._inject_tenant_id(data, tenant_id))

            cols_in_table = self._existing_columns(table)
            if "id" in cols_in_table and "id" not in row:
                row["id"] = str(uuid.uuid4())

            # Drop any keys that are not real columns (defensive — repositories
            # occasionally pass extras like virtual fields).
            row = {k: v for k, v in row.items() if k in cols_in_table}

            cols = list(row.keys())
            placeholders = ",".join(["?"] * len(cols))
            params = [_encode_value(c, row[c]) for c in cols]
            sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"

            with self._lock:
                self._conn.execute(sql, params)
                # Re-read by id when available so callers get authoritative data
                # (incl. defaulted timestamps).
                if "id" in row:
                    cur = self._conn.execute(
                        f"SELECT * FROM {table} WHERE id = ?", [row["id"]]
                    )
                    fetched = cur.fetchone()
                    return QueryResult(
                        data=[_decode_row(fetched)] if fetched else [row]
                    )
            return QueryResult(data=[row])
        except Exception as e:
            log.error(f"SQLite insert error on {table}: {e}")
            return QueryResult(data=[], error=str(e))

    def upsert(
        self,
        table: str,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        on_conflict: Optional[str] = None,
    ) -> QueryResult:
        try:
            row = dict(self._inject_tenant_id(data, tenant_id))
            cols_in_table = self._existing_columns(table)

            # Find existing row by the conflict key(s). Default heuristic for
            # ``brain_facts`` mirrors the production schema (key, tenant_id).
            conflict_keys: List[str]
            if on_conflict:
                conflict_keys = [c.strip() for c in on_conflict.split(",") if c.strip()]
            elif "key" in row and ("tenant_id" in cols_in_table or "org_id" in cols_in_table):
                conflict_keys = ["key", "tenant_id"]
            else:
                conflict_keys = ["id"] if "id" in row else []

            existing: Optional[sqlite3.Row] = None
            if conflict_keys and all(k in row or k in {"tenant_id", "org_id"} for k in conflict_keys):
                where_parts: List[str] = []
                params: List[Any] = []
                for k in conflict_keys:
                    if k == "tenant_id" and tenant_id:
                        frag, fp = self._tenant_filter_for(table, tenant_id)
                        if frag:
                            where_parts.append(frag)
                            params.extend(fp)
                    elif k in row:
                        where_parts.append(f"{k} = ?")
                        params.append(_encode_value(k, row[k]))
                if where_parts:
                    sql = f"SELECT * FROM {table} WHERE {' AND '.join(where_parts)} LIMIT 1"
                    with self._lock:
                        existing = self._conn.execute(sql, params).fetchone()

            if existing is not None:
                # UPDATE
                set_cols = [c for c in row.keys() if c in cols_in_table and c not in ("id",)]
                if not set_cols:
                    return QueryResult(data=[_decode_row(existing)])
                set_sql = ", ".join(f"{c} = ?" for c in set_cols)
                set_params = [_encode_value(c, row[c]) for c in set_cols]
                with self._lock:
                    self._conn.execute(
                        f"UPDATE {table} SET {set_sql} WHERE id = ?",
                        set_params + [existing["id"]],
                    )
                    fetched = self._conn.execute(
                        f"SELECT * FROM {table} WHERE id = ?", [existing["id"]]
                    ).fetchone()
                return QueryResult(data=[_decode_row(fetched)])

            # No match → INSERT.
            return self.insert(table, row, tenant_id=None)
        except Exception as e:
            log.error(f"SQLite upsert error on {table}: {e}")
            return QueryResult(data=[], error=str(e))

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        try:
            cols_in_table = self._existing_columns(table)
            set_cols = [c for c in data.keys() if c in cols_in_table]
            if not set_cols:
                return QueryResult(data=[])
            set_sql = ", ".join(f"{c} = ?" for c in set_cols)
            params: List[Any] = [_encode_value(c, data[c]) for c in set_cols]

            where: List[str] = []
            tenant_frag, tenant_params = self._tenant_filter_for(table, tenant_id)
            if tenant_frag:
                where.append(tenant_frag)
                params.extend(tenant_params)
            if filters:
                self._validate_columns(list(filters.keys()), cols_in_table)
                for k, v in filters.items():
                    where.append(f"{k} = ?")
                    params.append(_encode_value(k, v))

            sql = f"UPDATE {table} SET {set_sql}"
            if where:
                sql += " WHERE " + " AND ".join(where)

            with self._lock:
                self._conn.execute(sql, params)

            # Return the updated rows for parity with Supabase responses.
            return self.select(table=table, tenant_id=tenant_id, filters=filters)
        except Exception as e:
            log.error(f"SQLite update error on {table}: {e}")
            return QueryResult(data=[], error=str(e))

    def delete(
        self,
        table: str,
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        try:
            where: List[str] = []
            params: List[Any] = []
            tenant_frag, tenant_params = self._tenant_filter_for(table, tenant_id)
            if tenant_frag:
                where.append(tenant_frag)
                params.extend(tenant_params)
            if filters:
                existing_d = self._existing_columns(table)
                self._validate_columns(list(filters.keys()), existing_d)
                for k, v in filters.items():
                    where.append(f"{k} = ?")
                    params.append(_encode_value(k, v))

            sql = f"DELETE FROM {table}"
            if where:
                sql += " WHERE " + " AND ".join(where)
            with self._lock:
                self._conn.execute(sql, params)
            return QueryResult(data=[])
        except Exception as e:
            log.error(f"SQLite delete error on {table}: {e}")
            return QueryResult(data=[], error=str(e))

    def count(
        self,
        table: str,
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        result = self.select(
            table=table, columns="id", tenant_id=tenant_id, filters=filters, count=True
        )
        return result.count or 0
