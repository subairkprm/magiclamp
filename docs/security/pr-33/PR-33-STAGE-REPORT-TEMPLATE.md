# PR #33 Stage Report Template

Use this report after the WS-01 to WS-05 hardening bundle is implemented and verified.

```md
# PR #33 Stage Completion Report

## 1. Claim
State what is now true after PR #33.

## 2. Evidence
List exact files changed and key diff evidence.

## 3. Files Changed
Group by:
- Docker / Compose
- Nginx
- FastAPI config
- Env examples
- Docs
- Scripts

## 4. Validation Performed
Include command output summary:
- docker compose config
- docker ps port review
- verify-hardening.sh result
- relevant unit/smoke tests

## 5. Security Controls
Explain how PR #33 reduced exposure for:
- internal service ports
- CORS
- API docs
- N8N
- container hardening

## 6. UAE Data Residency Controls
Confirm:
- no cloud AI dependency added
- no hosted vector DB added
- no external agent endpoint added
- no new data egress path added

## 7. Remaining Risks
List anything still pending after WS-01 to WS-05.

## 8. Founder Action Needed
List only manual founder-side actions.

## 9. Next Stage Recommendation
State whether WS-06 can start.
```

## Minimum Completion Standard

PR #33 is complete only when:

- review checklist is complete
- verification script result is GREEN or accepted AMBER
- no unrelated scope is included
- rollback note is available
- founder decision is recorded
