# Magic Lamp Control Plane Contract v1

## Purpose
This contract defines boundary controls between the SpreadVerse **App Plane** and the Magic Lamp **Control Plane**.

## Plane Definitions
- **App Plane (SpreadVerse):** owns business logic, customer-facing workflows, domain models, and runtime application behavior.
- **Control Plane (Magic Lamp):** translates requests, plans workstreams, routes tasks, validates evidence, and reports status.

## Control Plane Scope (Allowed)
Magic Lamp may:
- Translate high-level requests into structured work items.
- Plan and sequence stages based on risk and dependencies.
- Route approved tasks to the correct execution path.
- Validate CI/security evidence and governance gates.
- Produce audit-friendly status and handoff reports.

## Prohibited Actions (Not Allowed)
Magic Lamp must **not**:
- Deploy infrastructure or applications.
- Merge pull requests.
- Run database migrations.
- Edit secrets, key material, or production credentials.

## Approval Model
- Any risky action (deployment, merge, schema change, permission change, production-impacting operation) requires explicit human approval.
- No agent may self-approve or auto-merge.

## Access Control
- Magic Lamp control-plane capabilities are **Super Admin-only**.
- Non-super-admin users and public traffic must not access control-plane operations.

## Enforcement Expectations
- Controls must be enforced by configuration, route guards, and CI policy checks.
- Violations should fail closed (deny action) and generate review evidence.

## Versioning
- Version: v1
- Effective date: 2026-05-19
- Owner: MagicLamp governance maintainers
