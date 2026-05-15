# PR #33 Rollback Note

PR #33 is intended to be a reversible security hardening bundle for WS-01 to WS-05.

## Rollback Principle

If deployment fails after merge, rollback should restore the previous Docker/Nginx/CORS behavior while keeping a clear incident note.

## Before Merge

Capture:

```bash
git rev-parse main
docker compose config > /tmp/magiclamp-compose-before-pr33.txt
docker ps --format '{{.Names}} {{.Ports}}' > /tmp/magiclamp-ports-before-pr33.txt
```

## After Merge

Capture:

```bash
git rev-parse main
docker compose config > /tmp/magiclamp-compose-after-pr33.txt
docker ps --format '{{.Names}} {{.Ports}}' > /tmp/magiclamp-ports-after-pr33.txt
```

## Rollback Command

If PR #33 is merged as a merge commit:

```bash
git revert -m 1 <merge_sha>
git push origin main
```

If PR #33 is squash-merged:

```bash
git revert <squash_commit_sha>
git push origin main
```

## VPS Rollback

After git rollback:

```bash
git pull origin main
docker compose config
docker compose up -d --build
bash docs/security/pr-33/verify-hardening.sh <VPS_IP> <DOMAIN>
```

## Incident Note Template

```md
Rollback performed for PR #33.

Reason:
Impact:
Rollback commit:
Verification result:
Remaining action:
```

## Important

Rollback is not a substitute for fixing the root cause. If rollback is used, keep the related WS issue open and create a follow-up fix PR.
