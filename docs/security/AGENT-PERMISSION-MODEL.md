# Agent Permission Model

> **RED / AMBER / GREEN action controls for all MagicLamp agents.**

---

## Overview

Every action an agent can take in MagicLamp is classified into one of three tiers:

| Tier | Colour | Meaning |
|------|--------|---------|
| **GREEN** | 🟢 | Permitted — agent can perform without additional approval |
| **AMBER** | 🟡 | Draft / Proposal only — agent can propose but not execute; requires human approval |
| **RED** | 🔴 | Blocked — agent cannot perform this action under any circumstances in MVP |

---

## RED Actions — Permanently Blocked in MVP

The following actions are **blocked** for all agents in MVP. No agent, regardless of tier, may perform these actions autonomously:

| Action ID | Description | Reason |
|-----------|-------------|--------|
| `push_code` | Push commits to any Git repository | Production code changes require human review |
| `merge_pr` | Merge a pull request | Merging is a human responsibility; irreversible |
| `deploy_vps` | Execute deployment scripts on VPS | Production deployments require human oversight |
| `delete_data` | Delete records from any database | Irreversible data loss risk |
| `modify_secrets` | Change `.env`, API keys, JWT secrets, or credentials | Credential compromise risk |
| `run_destructive_shell` | Execute shell commands with destructive effect (rm, drop, truncate, kill) | Irreversible system damage risk |
| `change_production_database` | Issue DDL or DML directly on production database tables | Schema and data integrity risk |
| `disable_audit_log` | Disable or bypass audit logging | Compliance and accountability requirement |
| `self_approve` | Approve an agent's own proposed customization | Conflict of interest / no-check bypass |
| `grant_own_permission` | Assign elevated permissions to itself | Privilege escalation risk |

**These actions are blocked at the framework level, not just by policy.** Any agent that attempts a RED action must receive a `PermissionDenied` error with audit log entry.

---

## AMBER Actions — Proposal Only (No Production Effect Without Approval)

The following actions are permitted as **drafts or proposals only**. An agent may prepare and store an AMBER action, but it cannot execute it without explicit human approval.

| Action ID | Description | Notes |
|-----------|-------------|-------|
| `propose_code_change` | Draft a code change suggestion | Stored as proposal; not committed |
| `propose_customization` | Draft a field/module/workflow customization | Stored in draft store; requires approval |
| `propose_deployment_change` | Suggest a deployment configuration change | Advisory note; not executed |
| `propose_rule_change` | Draft a new or modified business rule | Requires review before activation |
| `propose_workflow_activation` | Propose activating a new automated workflow | Requires approval before live |
| `propose_permission_change` | Suggest a role or permission adjustment | Requires founder/admin approval |
| `send_external_notification` | Send a notification outside the internal system | Requires approval for non-alert messages |

All AMBER actions are:
- Stored with version and timestamp
- Associated with the proposing agent ID
- Visible in the MagicLamp console for review
- Not executed until a GREEN signal is provided by an authorized approver

---

## GREEN Actions — Permitted Without Additional Approval

| Action ID | Description |
|-----------|-------------|
| `read_knowledge` | Read from RAG index, fact store, or knowledge base |
| `read_agent_state` | Read own or other agent's current state |
| `write_memory` | Write facts or memory to the agent's own store |
| `search_code` | Perform read-only code search or analysis |
| `generate_summary` | Produce a text summary of existing content |
| `answer_question` | Respond to a knowledge or advisory question |
| `generate_draft` | Create a draft document, plan, or explanation |
| `read_approved_api` | Query an approved read-only SpreadVerse API endpoint |
| `send_alert` | Send an internal Telegram/notification alert |
| `log_decision` | Write a decision record to the audit log |

---

## Customization Actions

As MagicLamp evolves toward a customization platform (Phase 2+), all customization actions start as **AMBER**:

- A customization action is never GREEN by default.
- A customization that has been approved multiple times and has a strong safety record may be elevated to a "pre-approved template" — but this requires explicit founder designation.
- No AI agent can apply a production customization without human approval at the point of each application.

---

## Permission Enforcement

Permissions are enforced through `brain/core/rbac.py`:

```python
from brain.core.rbac import WorkspaceRole, require, PermissionDenied

# Raises PermissionDenied (HTTP 403) if role cannot perform action
require(agent_role, Permission.WRITE_PRODUCTION)
```

- `PermissionDenied` is a subclass of `PermissionError`, which maps to HTTP 403 in FastAPI.
- All denied actions are written to the audit log.
- The RBAC matrix is deny-by-default — unknown permissions are denied.

---

## Audit Logging Requirement

Every RED action attempt and every AMBER action (proposed or approved) must generate an audit log entry:

```json
{
  "event": "action_blocked",
  "action_id": "push_code",
  "agent_id": "repo-advisor",
  "reason": "RED action blocked in MVP",
  "timestamp": "2026-05-15T08:00:00Z",
  "tenant_id": "default"
}
```

---

## Future Permission Evolution

As MagicLamp matures:
- RED actions may be elevated to AMBER (with approval) for specific, controlled scenarios.
- AMBER actions with strong track records may become GREEN for trusted agents.
- These changes require an explicit policy review and founder approval.
- No automated promotion of action tiers.

---

## Related Documents

- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](UAE-DATA-RESIDENCY-POLICY.md)
- [`docs/security/SECURITY-BASELINE.md`](SECURITY-BASELINE.md)
- [`docs/architecture/AGENT-REGISTRY.md`](../architecture/AGENT-REGISTRY.md)
- [`docs/product/MAGICLAMP-COMMAND-CENTER.md`](../product/MAGICLAMP-COMMAND-CENTER.md)
