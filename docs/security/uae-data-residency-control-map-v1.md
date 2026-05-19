# uae-data-residency-control-map-v1

## Purpose
Define the intended control map confirming MagicLamp control-plane data remains within UAE jurisdiction.

## Scope
All data stored or processed by the MagicLamp control plane.

## Control Objectives
- Ensure no customer PII is stored in MagicLamp.
- Prevent cross-border transfer of MagicLamp control-plane data.
- Maintain encryption in transit and at rest.

## Required Controls
- VPS hosting location is UAE datacenter (confirmed by infrastructure owner evidence).
- PostgreSQL data for MagicLamp is stored on UAE VPS infrastructure only.
- TLS 1.2+ is enforced on all inbound and service-to-service connections where applicable.
- Backups are stored only within UAE jurisdiction.
- No third-party cloud object storage (e.g., AWS S3, Google Cloud Storage) is permitted for control-plane data.
- Data classification for stored MagicLamp data is limited to Internal / Restricted.

Data explicitly NOT stored in MagicLamp:
- Customer documents
- Passwords
- Bank statements
- Raw emails
- Secrets
- Private keys
- Full production database data

## Validation and Evidence
Operator-provided evidence should be attached to review records, for example:
- VPS region confirmation from host/Coolify provisioning metadata or provider billing panel.
- TLS verification command output (example):
  - `openssl s_client -connect <internal-host>:443 -tls1_2`
- Backup location verification:
  - `find <backup-path> -maxdepth 2 -type f`
  - backup target configuration showing UAE-only storage endpoints.

This document is an intended control map and target baseline, not a formal certification artifact.

## Exceptions and Risk Acceptance
Exceptions require written founder/security approval and must document business justification, duration, and compensating controls.

## Review Cadence
Semi-annual.

## Owner and Approvals
Owner: Platform maintainer / Super Admin.
Approvals: Founder/security reviewer for exceptions and control-map updates.
