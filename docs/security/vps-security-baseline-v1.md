# vps-security-baseline-v1

## Purpose
Define the intended control baseline for hardening UAE-hosted MagicLamp control-plane VPS infrastructure and reducing infrastructure compromise risk.

## Scope
Applies to all VPS instances running MagicLamp via Coolify in the UAE-hosted control-plane environment.

## Control Objectives
- Prevent unauthorized access to VPS hosts.
- Reduce exposed attack surface at OS and container-host layers.
- Enforce least-privilege administrative access.

## Required Controls
- SSH key-only authentication is required; password authentication must be disabled.
- Root SSH login must be disabled.
- UFW firewall must be active and allow only required ports:
  - 80/tcp (HTTP)
  - 443/tcp (HTTPS)
  - 22/tcp (SSH) from known administrative IP ranges only
- `fail2ban` must be installed, enabled, and active.
- Unattended security upgrades must be enabled (`unattended-upgrades`).
- Unused network services must be disabled and not listening.
- Docker daemon must not be exposed on any public TCP port.

## Validation and Evidence
Collect evidence using operator-executed commands during review. Example validation commands:
- SSH authentication mode:
  - `sshd -T | grep -E 'passwordauthentication|pubkeyauthentication'`
- Root SSH login:
  - `sshd -T | grep permitrootlogin`
- Firewall posture:
  - `ufw status verbose`
  - `ss -tulpen`
- `fail2ban` status:
  - `systemctl status fail2ban`
  - `fail2ban-client status`
- Unattended upgrades:
  - `systemctl status unattended-upgrades`
  - `grep -R "Unattended-Upgrade" /etc/apt/apt.conf.d/`
- Unused services/ports:
  - `systemctl list-units --type=service --state=running`
  - `ss -tulpen`
- Docker daemon exposure:
  - `ss -ltnp | grep dockerd`
  - `ps aux | grep dockerd`

Note: This document defines an intended control baseline; it does not itself certify control operation.

## Exceptions and Risk Acceptance
No exceptions are permitted without written approval from the Super Admin and founder/security reviewer. Approved exceptions must include scope, rationale, expiry date, and compensating controls.

## Review Cadence
Quarterly.

## Owner and Approvals
Owner: Platform maintainer / Super Admin.
Approvals: Founder/security reviewer for any exception or baseline change.
