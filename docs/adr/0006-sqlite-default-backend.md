# ADR 0006 — SQLite as the default internal database

- **Status:** Accepted
- **Date:** 2026-05
- **Deciders:** Lead Architect
- **Tags:** backend, storage, deploy

## Context

`brain/core/database.py` was an abstract `DatabaseClient` with one concrete
implementation: `SupabaseClient`. Every code path that hit the database
required `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to be set, and `core/config.py`
treated those as mandatory at boot.

For self-hosters who want managed Postgres that's fine — but it makes the
"5-minute Railway deploy" story impossible. A Supabase project is several
clicks, requires another account, and has its own free-tier quotas to manage.
Worse, the `supabase` Python SDK pulls in transitive dependencies that conflict
with several common Python 3.11 environments.

## Decision

Add a second concrete implementation of `DatabaseClient`,
`brain/core/database_sqlite.py`, that stores everything in a single SQLite
file at `${BRAIN_DATA_DIR}/magiclamp.db`. The file lives on a Railway / Docker
volume so it survives restarts.

- A new `DB_BACKEND` env var (`sqlite` | `supabase`, default `sqlite`)
  controls which concrete client `get_database_client()` returns.
- `Settings.SUPABASE_URL` / `SUPABASE_SERVICE_KEY` become **optional**; the
  validator that previously rejected missing values now only runs when
  `DB_BACKEND=supabase`.
- The `supabase` Python package is loaded lazily inside `SupabaseClient`,
  `core/auth._get_supabase`, and `scheduler._get_supabase`. SQLite-only deploys
  never import it, so the simple deploy mode does not pull in the dependency
  at runtime.
- Tables are bootstrapped from a single bundled `brain/migrations/schema.sql`
  on first startup (idempotent, uses `CREATE TABLE IF NOT EXISTS`).
- Every method returns the same `QueryResult(success, data, error, count)`
  contract so existing repository code works unchanged on either backend.

## Consequences

**Positive**

- Zero-external-service deploys are possible. The Railway path is now: one
  container, one volume, one LLM key.
- Repositories don't change — they keep talking to `DatabaseClient` and the
  backend swap is transparent.
- Local development is faster: no network round-trips, instant test setup.
- The existing `test_rag.py` suite already used a hand-rolled in-memory
  `DatabaseClient`; SQLite generalises that pattern for production.

**Negative**

- SQLite is single-writer. Multi-instance horizontal scaling requires
  switching to `DB_BACKEND=supabase` (or another Postgres). The default
  Railway template uses `--workers 1` to keep this guarantee straightforward.
- Some Supabase-specific features (RLS policies, realtime channels, Postgres
  full-text search) are not available on the SQLite backend. Code paths that
  depend on them must check the backend or be feature-flagged.
- Two implementations to keep in sync. Mitigation: shared
  `QueryResult` contract + `tests/test_sqlite_backend.py` exercising the
  same `FactRepository` against both.

**Neutral**

- Existing Supabase deployments are unaffected. Setting `DB_BACKEND=supabase`
  restores the old behaviour exactly.

## Alternatives considered

- **Hosted Postgres on Railway by default.** Rejected per project guidance —
  the goal is "click Deploy on Railway, paste 1 LLM API key, paste 2 secrets,
  done." Adding a Postgres add-on doubles the moving parts and the cost.
- **DuckDB / LMDB.** Rejected — both are great for analytical workloads but
  poor at concurrent writes. SQLite's WAL mode handles MagicLamp's mostly
  single-writer workload well.
