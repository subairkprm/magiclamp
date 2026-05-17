# MagicLamp Agent Governance

This repository uses a strict governance model for all AI and human-assisted contributions.

## Product context
MagicLamp is a **controlled customization platform and AI command center**.

## Core operating rules
1. **One issue = one PR**. Never combine unrelated scope.
2. **No mixed workstreams**. Keep each PR aligned to a single defined workstream.
3. Agents **cannot merge PRs**.
4. Agents **cannot deploy to VPS**.
5. Agents **cannot run destructive shell commands** (`rm -rf`, force-reset history, etc.).
6. Agents **cannot modify production databases**.
7. Agents **cannot write directly to SpreadVerse V2 database**.
8. Agents **cannot bypass the RED/AMBER/GREEN permission model**.

## Hard gates (mandatory founder/security review)
Any PR touching these domains must be marked as **HARD GATE** and requires explicit human approval before merge:
- VPS/deployment changes
- Auth/security changes
- Database/schema changes
- Agent permission changes
- GitHub write access
- Production customization application
- External/cloud LLM usage
- Any data leaving UAE residency boundaries

## PR evidence requirements (mandatory)
Every PR must include all of the following sections:
- Claim
- Evidence
- Files changed
- Validation performed
- Security impact
- UAE data residency impact
- Remaining risk
- Founder action needed
- Next recommended workstream

## Non-goals for agents
- Do not close issues automatically.
- Do not merge anything automatically.
- Do not execute production-side operations.

See:
- `.agents/routing.md` for triage and gate routing.
- `.agents/handoff-template.md` for required PR handoff format.
- `.github/MERGE_VALIDATION_POLICY.md` for merge checks.
