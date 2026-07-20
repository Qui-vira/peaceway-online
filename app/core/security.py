"""Access gating - thin facade over the RBAC service.

Role membership is DB-backed (admin_users + assignments) with the env owner as
bootstrap. Permissions come from the code matrix in app.core.rbac.
"""
from __future__ import annotations

from app.core import rbac
from app.services.rbac_service import (  # re-export for convenience
    can,
    get_admin_id,
    get_role_keys,
    is_admin,
    log_activity,
    touch_activity,
)

__all__ = [
    "can", "get_admin_id", "get_role_keys", "is_admin", "log_activity",
    "touch_activity", "has", "primary_role",
]


def has(role_keys: set[str], permission: str) -> bool:
    """Synchronous permission check against an already-resolved role set."""
    return rbac.has_permission(role_keys, permission)


def primary_role(role_keys: set[str]) -> str | None:
    """Pick the highest-privilege role for display, by defined order."""
    for rk in rbac.ROLES:  # ROLES dict is ordered by privilege
        if rk in role_keys:
            return rk
    return None
