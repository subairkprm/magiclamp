# Backup & Rollback

> **Procedures for backing up MagicLamp data and rolling back to a previous state.**

---

## Backup Philosophy

MagicLamp stores its most valuable assets in:
1. **Supabase Postgres** — facts, memory, agent state, audit logs, users
2. **ChromaDB** — vector embeddings (RAG index)
3. **`.env`** — secrets and configuration
4. **N8N** — workflow definitions
5. **Ollama model files** — AI model weights (large, but reproducible)

Backups must be **encrypted** (because `.env` contains secrets) and stored on UAE infrastructure.

---

## What to Back Up

| Asset | Priority | Method |
|-------|----------|--------|
| Supabase Postgres database | 🔴 Critical | `pg_dump` |
| ChromaDB vector store | 🟡 Important | Directory snapshot |
| `.env` file | 🔴 Critical | Encrypted file copy |
| N8N workflow definitions | 🟡 Important | N8N export API |
| Ollama model files | 🟢 Low | Re-pullable from ollama.com |
| Application code | 🟢 Low | Git repository |

---

## Automated Backup

MagicLamp includes a `make backup` command that:

1. Dumps the Postgres database.
2. Snapshots the ChromaDB data directory.
3. Copies and encrypts `.env`.
4. Packages everything into a timestamped `.tar.gz` archive.
5. Stores the archive in `./backups/` on the VPS.

```bash
make backup
# Creates: backups/magiclamp-backup-YYYYMMDD-HHMMSS.tar.gz
```

### Backup Schedule Recommendation

| Frequency | Scope |
|-----------|-------|
| Daily (automated) | Full Postgres dump + ChromaDB snapshot + .env |
| Before every deployment | Full backup — always backup before `make deploy` |
| Weekly | Offload backup to encrypted UAE storage (S3-compatible, UAE region) |

---

## Manual Backup Procedure

If `make backup` is unavailable, perform these steps manually:

```bash
# 1. Dump Postgres
docker exec supabase-db pg_dump -U postgres magiclamp > /tmp/magiclamp-db.sql

# 2. Snapshot ChromaDB
tar -czf /tmp/chromadb-snapshot.tar.gz ./data/chromadb/

# 3. Copy .env (store securely — contains secrets)
cp .env /tmp/magiclamp.env

# 4. Package
tar -czf backups/magiclamp-manual-$(date +%Y%m%d-%H%M%S).tar.gz \
  /tmp/magiclamp-db.sql \
  /tmp/chromadb-snapshot.tar.gz \
  /tmp/magiclamp.env

# 5. Clean up temp files
rm /tmp/magiclamp-db.sql /tmp/chromadb-snapshot.tar.gz /tmp/magiclamp.env
```

---

## Restore Procedure

```bash
# Restore from a specific backup archive
make restore FILE=backups/magiclamp-backup-20260515-080000.tar.gz
```

### Manual Restore Steps

```bash
# 1. Stop the stack
make stop

# 2. Extract backup
tar -xzf backups/magiclamp-backup-YYYYMMDD-HHMMSS.tar.gz -C /tmp/restore/

# 3. Restore .env
cp /tmp/restore/magiclamp.env .env

# 4. Restore Postgres
docker exec -i supabase-db psql -U postgres magiclamp < /tmp/restore/magiclamp-db.sql

# 5. Restore ChromaDB
rm -rf ./data/chromadb/
tar -xzf /tmp/restore/chromadb-snapshot.tar.gz -C ./data/

# 6. Restart
make start
make status
```

---

## Rollback Procedure

### Code Rollback

If a code deployment causes issues:

```bash
# 1. Identify the last known good commit
git log --oneline -10

# 2. Roll back to previous commit
git checkout <previous-commit-sha>

# 3. Rebuild and redeploy
make build
make deploy

# 4. Verify health
make status
curl http://localhost:9000/health
```

### Database Rollback

If a migration or data change must be reversed:

1. Stop the Brain API: `docker compose stop brain`
2. Restore the Postgres dump from the pre-migration backup (see restore procedure above).
3. Restart: `docker compose start brain`
4. Verify: `curl http://localhost:9000/health`

> ⚠️ **Database rollback is destructive** — any data written after the backup point will be lost. Always take a backup immediately before any migration.

### Configuration Rollback

If a `.env` change causes issues:

```bash
# Restore previous .env from backup
tar -xzf backups/magiclamp-backup-YYYYMMDD-HHMMSS.tar.gz -C /tmp/restore/ magiclamp.env
cp /tmp/restore/magiclamp.env .env
make restart
```

---

## Backup Verification (Quarterly)

Every quarter, perform a restore test:

1. Spin up a staging environment (or use a local Docker environment).
2. Restore the most recent backup.
3. Verify the Brain API health endpoint.
4. Run a smoke test query against the reasoning API.
5. Confirm ChromaDB is serving vectors.
6. Document the test result with date and outcome.

---

## Backup Retention Policy

| Retention | Action |
|-----------|--------|
| Last 7 daily backups | Keep on VPS |
| Last 4 weekly backups | Keep on UAE-hosted encrypted storage |
| Monthly backups | Keep for 12 months on UAE-hosted encrypted storage |
| Older than 12 months | Review before deletion — founder approval required |

---

## Related Documents

- [`docs/operations/VPS-PRIVATE-DEPLOYMENT.md`](VPS-PRIVATE-DEPLOYMENT.md)
- [`docs/security/SECURITY-BASELINE.md`](../security/SECURITY-BASELINE.md)
- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md)
