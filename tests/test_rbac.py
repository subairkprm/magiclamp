"""Tests for the workspace RBAC matrix (brain/core/rbac.py)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")

from core.rbac import (  # noqa: E402
    Permission,
    PermissionDenied,
    WorkspaceRole,
    all_roles,
    can,
    permissions_for,
    require,
    role_at_least,
    role_rank,
)


# ── Role parsing ────────────────────────────────────────────────────


class TestWorkspaceRoleParse:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("owner", WorkspaceRole.OWNER),
            ("Owner", WorkspaceRole.OWNER),
            ("  ADMIN  ", WorkspaceRole.ADMIN),
            ("manager", WorkspaceRole.MANAGER),
            ("agent", WorkspaceRole.AGENT),
            ("viewer", WorkspaceRole.VIEWER),
        ],
    )
    def test_parse_accepts_case_insensitive_strings(self, raw, expected):
        assert WorkspaceRole.parse(raw) is expected

    def test_parse_passthrough_for_enum(self):
        assert WorkspaceRole.parse(WorkspaceRole.AGENT) is WorkspaceRole.AGENT

    @pytest.mark.parametrize("bad", ["", "root", "super_admin", None, 42])
    def test_parse_rejects_unknown_or_invalid(self, bad):
        with pytest.raises(ValueError):
            WorkspaceRole.parse(bad)


# ── Privilege ranking ───────────────────────────────────────────────


class TestRoleRanking:
    def test_rank_is_strictly_increasing(self):
        ranks = [role_rank(r) for r in all_roles()]
        assert ranks == sorted(set(ranks))
        assert role_rank(WorkspaceRole.OWNER) > role_rank(WorkspaceRole.ADMIN)
        assert role_rank(WorkspaceRole.ADMIN) > role_rank(WorkspaceRole.MANAGER)
        assert role_rank(WorkspaceRole.MANAGER) > role_rank(WorkspaceRole.AGENT)
        assert role_rank(WorkspaceRole.AGENT) > role_rank(WorkspaceRole.VIEWER)

    def test_role_at_least_handles_strings(self):
        assert role_at_least("admin", "manager") is True
        assert role_at_least("agent", "admin") is False
        assert role_at_least("owner", "owner") is True


# ── Deny-by-default + matrix ────────────────────────────────────────


class TestPermissionMatrix:
    def test_owner_has_every_permission(self):
        owner_perms = permissions_for(WorkspaceRole.OWNER)
        assert owner_perms == frozenset(Permission)

    def test_viewer_is_strictly_read_only(self):
        viewer_perms = permissions_for(WorkspaceRole.VIEWER)
        # No write/delete/manage permissions.
        for p in viewer_perms:
            assert "write" not in p.value
            assert "delete" not in p.value
            assert "manage" not in p.value
            assert "invite" not in p.value
            assert "configure" not in p.value
        # Must at least be able to read customers + facts and ask the AI.
        assert Permission.CUSTOMER_READ in viewer_perms
        assert Permission.FACT_READ in viewer_perms
        assert Permission.AI_ASK in viewer_perms

    def test_only_owner_can_manage_workspace(self):
        for r in all_roles():
            expected = r is WorkspaceRole.OWNER
            assert can(r, Permission.WORKSPACE_MANAGE) is expected

    def test_billing_is_owner_or_admin_only(self):
        allowed = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}
        for r in all_roles():
            assert can(r, Permission.WORKSPACE_BILLING) is (r in allowed)

    def test_member_role_change_is_owner_or_admin_only(self):
        allowed = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}
        for r in all_roles():
            assert can(r, Permission.MEMBER_ROLE_CHANGE) is (r in allowed)

    def test_agent_can_write_but_not_delete_or_export_customers(self):
        assert can(WorkspaceRole.AGENT, Permission.CUSTOMER_WRITE) is True
        assert can(WorkspaceRole.AGENT, Permission.CUSTOMER_DELETE) is False
        assert can(WorkspaceRole.AGENT, Permission.CUSTOMER_EXPORT) is False

    def test_manager_can_export_customers_for_pdpl_requests(self):
        # Managers handle PDPL "give me my data" requests; without export
        # they'd have to escalate every one to an admin.
        assert can(WorkspaceRole.MANAGER, Permission.CUSTOMER_EXPORT) is True

    def test_ai_configure_is_admin_or_owner_only(self):
        allowed = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}
        for r in all_roles():
            assert can(r, Permission.AI_CONFIGURE) is (r in allowed)


# ── can() / require() ───────────────────────────────────────────────


class TestCan:
    def test_can_accepts_permission_strings(self):
        assert can("owner", "workspace:manage") is True
        assert can("viewer", "customer:write") is False

    def test_can_returns_false_for_unknown_permission_string(self):
        # Typo in a route must NEVER be treated as "permitted".
        assert can("owner", "customer:nuke-from-orbit") is False

    def test_can_raises_for_unknown_role(self):
        with pytest.raises(ValueError):
            can("god-mode", Permission.CUSTOMER_READ)


class TestRequire:
    def test_require_passes_silently_when_permitted(self):
        require(WorkspaceRole.AGENT, Permission.CUSTOMER_WRITE)  # no exception

    def test_require_raises_permission_denied_when_not(self):
        with pytest.raises(PermissionDenied) as ei:
            require(WorkspaceRole.VIEWER, Permission.CUSTOMER_DELETE)
        assert ei.value.role is WorkspaceRole.VIEWER
        assert ei.value.permission is Permission.CUSTOMER_DELETE
        # Must inherit PermissionError so existing FastAPI handlers (which
        # map PermissionError → 403) keep working without changes.
        assert isinstance(ei.value, PermissionError)

    def test_require_denies_unknown_permission_string(self):
        with pytest.raises(PermissionDenied):
            require(WorkspaceRole.OWNER, "customer:nuke-from-orbit")
