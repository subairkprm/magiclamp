"""Workspace RBAC — role enum, permission matrix, and access helpers.

Phase 1 of the UAE-market plan introduces *workspaces* (a tenant + its team)
and a per-workspace role on every membership. This module is the single
source of truth for what each role may do; every API handler (and the
upcoming Next.js shell, through a thin mirror) MUST consult it via
:func:`can` / :func:`require` rather than hand-rolling role string checks.

Design choices:

* **Deny by default.** A permission a role does not appear under is denied,
  no matter how the caller spells the role string.
* **Five workspace roles**, ordered by privilege:

  Owner > Admin > Manager > Agent > Viewer

  matching ``ROADMAP.md`` Phase 1. The existing top-level ``User.role``
  ("user" / "admin" / "agent" / "super_admin") is *unchanged* — it
  controls the brain platform itself; workspace roles control what a member
  can do *inside* one workspace.
* **String-friendly.** Roles deserialise from the case-insensitive name so
  JWT claims and DB columns can keep storing plain strings.
* **No external dependencies.** Pure stdlib so this can be reused by
  scripts, the scheduler, and tests without dragging FastAPI / Pydantic in.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Iterable


class WorkspaceRole(str, Enum):
    """The five workspace-level roles. ``str`` mixin so JSON-friendly."""

    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"

    @classmethod
    def parse(cls, value: "str | WorkspaceRole") -> "WorkspaceRole":
        """Case-insensitive parse from a string. Raises ``ValueError``.

        Handy because role strings come from JWT claims, env files and CSV
        imports where casing isn't guaranteed.
        """
        if isinstance(value, WorkspaceRole):
            return value
        if not isinstance(value, str) or not value:
            raise ValueError(f"Invalid workspace role: {value!r}")
        try:
            return cls(value.strip().lower())
        except ValueError as e:
            raise ValueError(
                f"Unknown workspace role {value!r}; expected one of "
                f"{[r.value for r in cls]}"
            ) from e


# Privilege rank — higher means more privileged. Used by ``role_at_least``
# and by the membership-management permissions below.
_RANK: Dict[WorkspaceRole, int] = {
    WorkspaceRole.VIEWER: 1,
    WorkspaceRole.AGENT: 2,
    WorkspaceRole.MANAGER: 3,
    WorkspaceRole.ADMIN: 4,
    WorkspaceRole.OWNER: 5,
}


def role_rank(role: "str | WorkspaceRole") -> int:
    """Return the privilege rank of ``role`` (1 = Viewer, 5 = Owner)."""
    return _RANK[WorkspaceRole.parse(role)]


def role_at_least(
    role: "str | WorkspaceRole", minimum: "str | WorkspaceRole"
) -> bool:
    """True iff ``role`` is at least as privileged as ``minimum``."""
    return role_rank(role) >= role_rank(minimum)


class Permission(str, Enum):
    """Atomic actions a workspace role may or may not perform.

    The names are domain-flavoured (``customer:read``) on purpose — they are
    what audit-log lines and PDPL access reports will quote verbatim.
    """

    # Workspace + members
    WORKSPACE_MANAGE = "workspace:manage"           # rename, delete, transfer ownership
    WORKSPACE_BILLING = "workspace:billing"          # view invoices, change plan
    MEMBER_INVITE = "member:invite"
    MEMBER_REMOVE = "member:remove"
    MEMBER_ROLE_CHANGE = "member:role_change"

    # Customer 360
    CUSTOMER_READ = "customer:read"
    CUSTOMER_WRITE = "customer:write"
    CUSTOMER_DELETE = "customer:delete"
    CUSTOMER_EXPORT = "customer:export"              # GDPR/PDPL data export

    # Brain / facts
    FACT_READ = "fact:read"
    FACT_WRITE = "fact:write"
    FACT_DELETE = "fact:delete"

    # AI / LLM
    AI_ASK = "ai:ask"                                 # use the assistant
    AI_CONFIGURE = "ai:configure"                    # change provider, prompts

    # Audit + integrations
    AUDIT_READ = "audit:read"
    INTEGRATION_MANAGE = "integration:manage"        # WhatsApp, Stripe, Telr, Tabby


# Permission matrix — explicit per role for readability. Anything not listed
# is denied. Keep this matrix sorted by descending privilege so reviewers can
# eyeball "who got what" in one glance.
_MATRIX: Dict[WorkspaceRole, FrozenSet[Permission]] = {
    WorkspaceRole.OWNER: frozenset(Permission),  # Owner is omnipotent inside their workspace
    WorkspaceRole.ADMIN: frozenset(
        {
            Permission.WORKSPACE_BILLING,
            Permission.MEMBER_INVITE,
            Permission.MEMBER_REMOVE,
            Permission.MEMBER_ROLE_CHANGE,
            Permission.CUSTOMER_READ,
            Permission.CUSTOMER_WRITE,
            Permission.CUSTOMER_DELETE,
            Permission.CUSTOMER_EXPORT,
            Permission.FACT_READ,
            Permission.FACT_WRITE,
            Permission.FACT_DELETE,
            Permission.AI_ASK,
            Permission.AI_CONFIGURE,
            Permission.AUDIT_READ,
            Permission.INTEGRATION_MANAGE,
        }
    ),
    WorkspaceRole.MANAGER: frozenset(
        {
            Permission.MEMBER_INVITE,
            Permission.CUSTOMER_READ,
            Permission.CUSTOMER_WRITE,
            Permission.CUSTOMER_EXPORT,
            Permission.FACT_READ,
            Permission.FACT_WRITE,
            Permission.AI_ASK,
            Permission.AUDIT_READ,
        }
    ),
    WorkspaceRole.AGENT: frozenset(
        {
            Permission.CUSTOMER_READ,
            Permission.CUSTOMER_WRITE,
            Permission.FACT_READ,
            Permission.FACT_WRITE,
            Permission.AI_ASK,
        }
    ),
    WorkspaceRole.VIEWER: frozenset(
        {
            Permission.CUSTOMER_READ,
            Permission.FACT_READ,
            Permission.AI_ASK,
        }
    ),
}


class PermissionDenied(PermissionError):
    """Raised by :func:`require` when a role lacks the requested permission.

    Inherits ``PermissionError`` so existing FastAPI exception handlers that
    map ``PermissionError`` → 403 keep working unchanged.
    """

    def __init__(self, role: WorkspaceRole, permission: Permission):
        self.role = role
        self.permission = permission
        super().__init__(
            f"Workspace role {role.value!r} is not permitted to {permission.value!r}"
        )


def can(role: "str | WorkspaceRole", permission: "str | Permission") -> bool:
    """Return True iff ``role`` is granted ``permission``. Deny by default.

    Accepts strings on both sides for ergonomic use from request handlers
    that hold raw JWT claim values.
    """
    parsed_role = WorkspaceRole.parse(role)
    if isinstance(permission, str):
        try:
            parsed_perm = Permission(permission)
        except ValueError:
            # Unknown permission → deny. Don't blow up on a typo in a route,
            # but never silently allow it either.
            return False
    else:
        parsed_perm = permission
    return parsed_perm in _MATRIX[parsed_role]


def require(
    role: "str | WorkspaceRole", permission: "str | Permission"
) -> None:
    """Raise :class:`PermissionDenied` if ``role`` lacks ``permission``."""
    parsed_role = WorkspaceRole.parse(role)
    if isinstance(permission, str):
        try:
            parsed_perm = Permission(permission)
        except ValueError as e:
            # Treat unknown permission as denied with a clear error.
            raise PermissionDenied(parsed_role, Permission.WORKSPACE_MANAGE) from e
    else:
        parsed_perm = permission
    if parsed_perm not in _MATRIX[parsed_role]:
        raise PermissionDenied(parsed_role, parsed_perm)


def permissions_for(role: "str | WorkspaceRole") -> FrozenSet[Permission]:
    """Return the (frozen) set of permissions granted to ``role``."""
    return _MATRIX[WorkspaceRole.parse(role)]


def all_roles() -> Iterable[WorkspaceRole]:
    """Iterate the five workspace roles in ascending privilege order."""
    return sorted(WorkspaceRole, key=lambda r: _RANK[r])


__all__ = [
    "WorkspaceRole",
    "Permission",
    "PermissionDenied",
    "can",
    "require",
    "permissions_for",
    "role_rank",
    "role_at_least",
    "all_roles",
]
