# incident-response-sop-v1

## Purpose
Define standard operating procedures for responding to security incidents that affect MagicLamp control-plane availability, integrity, or confidentiality.

## Scope
Any unauthorized access attempt, data exposure event, service disruption, or agent misbehavior involving MagicLamp.

## Control Objectives
- Detect and triage incidents quickly.
- Contain blast radius and prevent further impact.
- Preserve evidence for root-cause analysis and corrective action.

## Required Controls
Severity classification:
- **P1:** Production unavailable or confirmed data exposure.
- **P2:** Suspected breach or materially degraded service.
- **P3:** Security anomaly detected with no confirmed impact.

Detection triggers (examples):
- `fail2ban` alerts.
- Unexpected open ports or new listeners.
- CI secret scanning failure.
- Unauthorized API call attempts to control-plane interfaces.

Containment steps:
1. Isolate affected control-plane container/service (example: `docker stop brain`) when safe to do so.
2. Revoke/rotate exposed secrets immediately.
3. Preserve logs and forensic artifacts before restart/rebuild.
4. Notify Super Admin within 1 hour for all P1/P2 incidents.

Post-incident requirements:
- Root cause analysis completed within 48 hours for P1/P2.
- Control updates and corrective actions documented.
- Incident recorded under `docs/security/incident-log/`.

## Validation and Evidence
For each incident, retain:
- Timeline of detection, containment, recovery, and communication.
- Command outputs/log excerpts used in triage.
- Evidence of secret rotation and control remediation.
- Linked RCA document and follow-up action tracker.

This SOP is an intended control process and target operational baseline, not a formal certification statement.

## Exceptions and Risk Acceptance
No deviation from P1/P2 notification and containment requirements without written founder/security approval.

## Review Cadence
After every P1/P2 incident and during an annual incident response drill.

## Owner and Approvals
Owner: Platform maintainer / Super Admin.
Approvals: Founder/security reviewer for SOP exceptions and significant procedural changes.
