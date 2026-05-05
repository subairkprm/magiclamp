#!/usr/bin/env python3
"""Backfill the vector store with embeddings for every fact in ``brain_facts``.

Usage:
    python scripts/backfill_embeddings.py [--tenant TENANT_ID] [--batch-size N]

The script is idempotent because vector ids are derived from
``(tenant_id, key)`` — re-running simply upserts the same documents.

By default, all tenants discovered in ``brain_facts`` are backfilled. Pass
``--tenant`` to limit to a single tenant. The script does not require
``RAG_ENABLED`` to be true at runtime; it always uses the configured
:class:`VectorStore`.
"""

from __future__ import annotations

import argparse
import os
import sys

# Allow running from repo root: `python scripts/backfill_embeddings.py`
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "brain"))

from core.database import get_database_client  # noqa: E402
from core.vector_store import get_vector_store  # noqa: E402
from repositories import FactRepository  # noqa: E402


def discover_tenants(db, page_size: int = 1000) -> list:
    """Return distinct tenant_ids present in brain_facts (paginated)."""
    seen = set()
    offset = 0
    while True:
        # DatabaseClient has no offset primitive, so we page via limit and
        # rely on stable ordering by id. For very large fact tables consider
        # passing --tenant explicitly.
        res = db.select(
            table="brain_facts",
            columns="tenant_id,org_id,id",
            order_by="id.asc",
            limit=page_size,
        )
        if not res.success:
            print(f"WARN: could not enumerate tenants: {res.error}", file=sys.stderr)
            return sorted(seen)
        rows = res.data or []
        for row in rows:
            for k in ("tenant_id", "org_id"):
                v = row.get(k)
                if v:
                    seen.add(v)
        # No native offset; if the page wasn't full we're done.
        if len(rows) < page_size:
            break
        # Without offset support, iterating further would re-read the same
        # rows. Break and warn so operators know to pass --tenant for
        # very large deployments.
        print(
            f"NOTE: discovered {len(seen)} tenant(s) in first page of "
            f"{page_size} rows; pass --tenant to backfill specific tenants "
            "in larger deployments.",
            file=sys.stderr,
        )
        break
    return sorted(seen)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tenant", help="Only backfill this tenant_id (default: all)")
    p.add_argument("--batch-size", type=int, default=64, help="Embedding batch size")
    args = p.parse_args()

    db = get_database_client()
    vs = get_vector_store()  # surface init errors loudly here
    print(f"Vector store ready: {type(vs).__name__}")

    tenants = [args.tenant] if args.tenant else discover_tenants(db)
    if not tenants:
        print("No tenants found; nothing to backfill.")
        return 0

    repo = FactRepository(db, vector_store=vs)
    grand_total = 0
    for tenant_id in tenants:
        print(f"-> tenant={tenant_id}")
        n = repo.reindex_all(tenant_id=tenant_id, batch_size=args.batch_size)
        print(f"   indexed {n} facts")
        grand_total += n

    print(f"Done. Indexed {grand_total} facts across {len(tenants)} tenant(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
