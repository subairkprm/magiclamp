-- MagicLamp SQLite schema
-- This schema is created automatically by SQLiteClient on first startup.
-- All tables mirror the structure used by the existing Supabase deployment so
-- that repository code can be reused unchanged.
--
-- JSON-typed columns are stored as TEXT and (de)serialised by SQLiteClient.
-- Tenant scoping uses a single ``tenant_id`` column on every tenant-scoped
-- table; the ``org_id`` alias supported by SupabaseClient is normalised to
-- ``tenant_id`` at insert/upsert time.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ── Organizations (tenants themselves) ─────────────────────────────
CREATE TABLE IF NOT EXISTS organizations (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'free',
    is_active   INTEGER NOT NULL DEFAULT 1,
    settings    TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Users ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_login      TEXT
);
CREATE INDEX IF NOT EXISTS users_tenant_email_idx ON users(tenant_id, email);

-- ── Brain facts ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS brain_facts (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT,
    key         TEXT NOT NULL,
    value       TEXT,                      -- JSON-serialised
    source      TEXT NOT NULL DEFAULT 'api',
    confidence  REAL NOT NULL DEFAULT 1.0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (tenant_id, key)
);

-- ── Events / observations ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT,
    event_type  TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    data        TEXT NOT NULL DEFAULT '{}',
    summary     TEXT NOT NULL DEFAULT '',
    importance  INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Training data ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS training_data (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT,
    input       TEXT NOT NULL,
    output      TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'manual',
    quality     REAL NOT NULL DEFAULT 1.0,
    verified    INTEGER NOT NULL DEFAULT 0,
    context     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Decisions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT,
    trigger     TEXT NOT NULL,
    reasoning   TEXT NOT NULL,
    action      TEXT NOT NULL,
    confidence  REAL NOT NULL DEFAULT 0.5,
    outcome     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── API keys ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT,
    name            TEXT NOT NULL,
    key_hash        TEXT NOT NULL,
    key_prefix      TEXT NOT NULL,
    scopes          TEXT NOT NULL DEFAULT '[]',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_by      TEXT,
    last_used_at    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Webhooks ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS webhooks (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    events          TEXT NOT NULL DEFAULT '[]',
    is_active       INTEGER NOT NULL DEFAULT 1,
    secret          TEXT,
    last_called     TEXT,
    failure_count   INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Integrations ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS integrations (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    config      TEXT NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'inactive',
    last_sync   TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Audit log ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT,
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT,
    user_id         TEXT,
    old_data        TEXT,
    new_data        TEXT,
    ip_address      TEXT,
    user_agent      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Subscription plans (global, not tenant-scoped) ────────────────
CREATE TABLE IF NOT EXISTS subscription_plans (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    price_monthly   REAL NOT NULL DEFAULT 0.0,
    price_yearly    REAL NOT NULL DEFAULT 0.0,
    features        TEXT NOT NULL DEFAULT '{}',
    "limits"        TEXT NOT NULL DEFAULT '{}',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Teams ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teams (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT,
    name        TEXT NOT NULL,
    description TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS team_members (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT,
    team_id     TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'member',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── LLM provider preferences (per tenant) ─────────────────────────
-- Stores the user-selected LLM provider/model for a tenant. API keys live in
-- env vars (never the database) for safety; this table only persists the
-- runtime selection.
CREATE TABLE IF NOT EXISTS llm_settings (
    tenant_id   TEXT PRIMARY KEY,
    provider    TEXT NOT NULL,
    model       TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
