# backup-restore-policy-v1

## Purpose
Define the intended backup and restore baseline to ensure MagicLamp control-plane metadata can be recovered after failure.

## Scope
MagicLamp isolated PostgreSQL database containing metadata tables only (no customer data).

## Control Objectives
- Ensure recoverability within defined time and data-loss tolerances.
- Keep backup data encrypted and region-restricted to UAE jurisdiction.
- Prevent insecure or unauthorized backup handling.

## Required Controls
- Backup frequency: Daily automated database backup.
- Retention: 30 days minimum.
- Storage location: UAE VPS local storage plus encrypted offsite backup within UAE jurisdiction only.
- Encryption:
  - At rest: AES-256.
  - In transit: TLS.
- Restore testing: Monthly restore drill into staging environment.
- Recovery targets:
  - RTO: 4 hours.
  - RPO: 24 hours.
- Prohibited:
  - No backup copies to foreign cloud storage.
  - No unencrypted backup files.

## Validation and Evidence
Representative evidence artifacts:
- Backup scheduler/job logs confirming daily runs.
- Backup inventory showing retention window and storage location.
- Encryption configuration evidence for at-rest and in-transit controls.
- Monthly restore drill records with outcome and recovery timing.

This document establishes intended controls and a target baseline; it does not itself attest formal compliance.

## Exceptions and Risk Acceptance
Exceptions require written founder/security approval with compensating controls, expiry date, and documented residual risk.

## Review Cadence
Quarterly.

## Owner and Approvals
Owner: Platform maintainer / Super Admin.
Approvals: Founder/security reviewer for policy exceptions and control changes.
