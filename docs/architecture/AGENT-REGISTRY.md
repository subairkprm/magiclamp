# Agent Registry

> **How MagicLamp agents are registered, discovered, and governed.**

---

## Purpose

The Agent Registry is the single authoritative list of agents that MagicLamp knows about and can coordinate. It defines:

- What each agent is allowed to do (permission tier)
- What each agent's current state is (active, disabled, suspended)
- How agents are discovered and invoked
- How agent health is monitored

---

## Agent Lifecycle

```
REGISTERED → ACTIVE → SUSPENDED → DEREGISTERED
                │
                ▼
            DISABLED
```

| State | Description |
|-------|-------------|
| `REGISTERED` | Agent is known to the registry but not yet approved for use |
| `ACTIVE` | Agent is running and accepting tasks |
| `SUSPENDED` | Agent is temporarily paused (e.g. permission review, failure threshold) |
| `DISABLED` | Agent is permanently disabled for this environment |
| `DEREGISTERED` | Agent has been removed from the registry |

---

## Agent Permission Tiers

Every registered agent is assigned a permission tier. Tiers map to the action permission model.

| Tier | Label | Description |
|------|-------|-------------|
| `T0` | Read-Only | Can only read knowledge, facts, memory, and RAG index |
| `T1` | Advisory | Can read and produce draft proposals; cannot write anything |
| `T2` | Controlled Write | Can write to agent-internal state and draft store; cannot touch production |
| `T3` | Supervised Action | Can take limited production actions with per-action human approval |
| `T4` | Restricted Admin | Reserved for founder-level agents; all actions logged and reviewable |

MVP agents should be `T0` or `T1` only. No agent starts at `T3` or `T4` without explicit founder approval.

---

## Core Agents (MVP)

| Agent ID | Name | Tier | Description |
|----------|------|------|-------------|
| `brain-core` | Brain Core | T2 | Central reasoning, memory, and RAG agent |
| `scheduler` | Autonomous Scheduler | T2 | Background jobs — briefings, scoring, snapshots |
| `repo-advisor` | Repo Advisor | T1 | Explains codebase, surfaces PR summaries, advisory only |
| `deployment-advisor` | Deployment Advisor | T1 | Explains deployment state, surfaces risks, advisory only |
| `knowledge-curator` | Knowledge Curator | T2 | Ingests, indexes, and maintains the RAG knowledge base |
| `customization-drafter` | Customization Drafter | T1 | Drafts customization proposals (Phase 2+) — no production writes |

---

## Registry Entry Structure

Each agent is described by a registry entry:

```json
{
  "agent_id": "repo-advisor",
  "name": "Repo Advisor",
  "tier": "T1",
  "state": "ACTIVE",
  "capabilities": ["read_code", "summarise_pr", "explain_workstream"],
  "blocked_actions": ["push_code", "merge_pr", "deploy_vps"],
  "last_health_check": "2026-05-15T08:00:00Z",
  "owner": "brain-core",
  "created_at": "2026-05-01T00:00:00Z"
}
```

---

## Health Monitoring

- Each active agent exposes a health check endpoint or heartbeat signal.
- The Brain Core monitors agent health every 60 seconds.
- If an agent fails to respond after 3 consecutive checks, it is moved to `SUSPENDED`.
- Telegram alert is sent when an agent is suspended.

---

## Registering a New Agent

To register a new agent in MagicLamp:

1. Define the agent's capabilities and required permission tier.
2. Get founder/admin approval for the tier assignment.
3. Add the agent entry to the registry (via API or configuration file).
4. Assign the agent to a workspace role if it interacts with workspace resources.
5. Run the agent in `REGISTERED` state (no tasks) for one observation period.
6. Promote to `ACTIVE` after observation passes.

---

## Future: WS-17 Agent Registry Implementation

The formal Agent Registry implementation is planned for **WS-17**. This document defines the design intent. The current implementation uses the RBAC and permission system from `brain/core/rbac.py` as the enforcement layer.

See [`docs/security/AGENT-PERMISSION-MODEL.md`](../security/AGENT-PERMISSION-MODEL.md) for the full action permission model.

---

## Related Documents

- [`docs/security/AGENT-PERMISSION-MODEL.md`](../security/AGENT-PERMISSION-MODEL.md)
- [`docs/architecture/OFFLINE-AGENT-ARCHITECTURE.md`](OFFLINE-AGENT-ARCHITECTURE.md)
- [`docs/product/MAGICLAMP-COMMAND-CENTER.md`](../product/MAGICLAMP-COMMAND-CENTER.md)
