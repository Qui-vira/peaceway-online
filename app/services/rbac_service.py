"""RBAC runtime service: resolve roles, check permissions, route alerts, log activity.

Role membership lives in the DB (`admin_users` + `admin_role_assignments`). The
System Owner is bootstrapped from `OWNER_TELEGRAM_IDS` so the developer always has
access even before any DB rows exist.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.config import get_settings
from app.core.db import get_session
from app.models import AdminActivityLog, AdminRoleAssignment, AdminUser
from app.models.admin import AdminStatus


@asynccontextmanager
async def _scope(session: AsyncSession | None):
    """Use an injected session (tests) if given, else open the real DB session."""
    if session is not None:
        yield session
    else:
        async with get_session() as s:
            yield s


async def get_role_keys(telegram_id: int, session: AsyncSession | None = None) -> set[str]:
    """Resolve the set of active role keys for a Telegram user."""
    settings = get_settings()
    bootstrap: set[str] = {rbac.SYSTEM_OWNER} if telegram_id in settings.owner_ids else set()

    async def _query(s: AsyncSession) -> set[str]:
        admin = (
            await s.execute(select(AdminUser).where(AdminUser.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if admin is None or not admin.is_active:
            return set()
        return {a.role_key for a in admin.assignments}

    if session is not None:
        return bootstrap | await _query(session)
    async with get_session() as s:
        return bootstrap | await _query(s)


async def can(telegram_id: int, permission: str) -> bool:
    roles = await get_role_keys(telegram_id)
    return rbac.has_permission(roles, permission)


async def is_admin(telegram_id: int) -> bool:
    return bool(await get_role_keys(telegram_id))


async def touch_activity(telegram_id: int) -> None:
    async with get_session() as s:
        await s.execute(
            update(AdminUser)
            .where(AdminUser.telegram_id == telegram_id)
            .values(last_activity_at=datetime.now(timezone.utc))
        )


async def log_activity(
    telegram_id: int, roles: set[str], action: str, entity: str | None = None,
    entity_id: str | None = None, detail: dict | None = None,
) -> None:
    async with get_session() as s:
        s.add(
            AdminActivityLog(
                telegram_id=telegram_id,
                roles=",".join(sorted(roles)) if roles else None,
                action=action,
                entity=entity,
                entity_id=entity_id,
                detail=detail,
            )
        )


async def recipients_for_roles(
    target_roles: set[str], session: AsyncSession | None = None
) -> tuple[set[int], list[str]]:
    """Return (telegram_ids, emails) of active admins holding any target role.

    Env-bootstrap owners are always included for System-Owner-targeted alerts.
    """
    settings = get_settings()
    telegram_ids: set[int] = set()
    emails: set[str] = set()

    async with _scope(session) as s:
        rows = (
            await s.execute(
                select(AdminUser)
                .join(AdminRoleAssignment, AdminRoleAssignment.admin_id == AdminUser.id)
                .where(AdminUser.is_active.is_(True), AdminRoleAssignment.role_key.in_(target_roles))
            )
        ).scalars().unique().all()
    for a in rows:
        telegram_ids.add(a.telegram_id)
        if a.email:
            emails.add(a.email)

    if rbac.SYSTEM_OWNER in target_roles:
        telegram_ids |= settings.owner_ids

    return telegram_ids, sorted(emails)


async def seed_roles_and_permissions() -> None:
    """Sync the roles/permissions/role_permissions tables from the code matrix."""
    from app.models import Permission, Role, RolePermission

    async with get_session() as s:
        existing_roles = {r.key for r in (await s.execute(select(Role))).scalars().all()}
        for key, name in rbac.ROLES.items():
            if key not in existing_roles:
                s.add(Role(key=key, name=name))

        existing_perms = {p.key for p in (await s.execute(select(Permission))).scalars().all()}
        for key, desc in rbac.PERMISSIONS.items():
            if key not in existing_perms:
                s.add(Permission(key=key, description=desc))

        existing_rp = {
            (rp.role_key, rp.permission_key)
            for rp in (await s.execute(select(RolePermission))).scalars().all()
        }
        for role_key, perms in rbac.ROLE_PERMISSIONS.items():
            for perm in perms:
                if perm == rbac.WILDCARD:
                    continue
                if (role_key, perm) not in existing_rp:
                    s.add(RolePermission(role_key=role_key, permission_key=perm))


async def add_admin(
    telegram_id: int, role_key: str, full_name: str | None = None, email: str | None = None,
    session: AsyncSession | None = None,
) -> AdminUser:
    """Add a role to a (possibly new) admin.

    Brand-new admins, and anyone previously REMOVED, start PENDING — the Owner
    must explicitly Activate before they gain access. Adding a role to an
    already PENDING/ACTIVE/DISABLED admin leaves their status untouched.
    """
    async with _scope(session) as s:
        admin = (
            await s.execute(select(AdminUser).where(AdminUser.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if admin is None:
            admin = AdminUser(
                telegram_id=telegram_id, full_name=full_name, email=email,
                is_active=False, status=AdminStatus.PENDING,
            )
            s.add(admin)
            await s.flush()
        else:
            if full_name:
                admin.full_name = full_name
            if email:
                admin.email = email
            if admin.status == AdminStatus.REMOVED:
                admin.status = AdminStatus.PENDING
                admin.is_active = False
        exists = (
            await s.execute(
                select(AdminRoleAssignment).where(
                    AdminRoleAssignment.admin_id == admin.id,
                    AdminRoleAssignment.role_key == role_key,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            s.add(AdminRoleAssignment(admin_id=admin.id, role_key=role_key))
        await s.flush()
        return admin


async def activate_admin(telegram_id: int, session: AsyncSession | None = None) -> bool:
    """Grant access to a PENDING or DISABLED admin."""
    async with _scope(session) as s:
        result = await s.execute(
            update(AdminUser)
            .where(AdminUser.telegram_id == telegram_id, AdminUser.status != AdminStatus.REMOVED)
            .values(status=AdminStatus.ACTIVE, is_active=True)
        )
        return result.rowcount > 0


async def disable_admin(telegram_id: int, session: AsyncSession | None = None) -> bool:
    """Temporarily suspend access. Roles are preserved for a later reactivation."""
    async with _scope(session) as s:
        result = await s.execute(
            update(AdminUser)
            .where(AdminUser.telegram_id == telegram_id)
            .values(status=AdminStatus.DISABLED, is_active=False)
        )
        return result.rowcount > 0


async def remove_admin(telegram_id: int, session: AsyncSession | None = None) -> bool:
    """Soft-remove: clear role assignments immediately, keep the row + audit history."""
    async with _scope(session) as s:
        admin = (
            await s.execute(select(AdminUser).where(AdminUser.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if admin is None:
            return False
        admin.status = AdminStatus.REMOVED
        admin.is_active = False
        await s.execute(delete(AdminRoleAssignment).where(AdminRoleAssignment.admin_id == admin.id))
        return True


async def remove_admin_role(telegram_id: int, role_key: str, session: AsyncSession | None = None) -> bool:
    async with _scope(session) as s:
        admin = (
            await s.execute(select(AdminUser).where(AdminUser.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if admin is None:
            return False
        result = await s.execute(
            delete(AdminRoleAssignment).where(
                AdminRoleAssignment.admin_id == admin.id, AdminRoleAssignment.role_key == role_key
            )
        )
        return result.rowcount > 0


async def search_admins(query: str, limit: int = 10, session: AsyncSession | None = None) -> list[AdminUser]:
    """Search admins by name (partial) or exact numeric Telegram ID."""
    q = query.strip()
    async with _scope(session) as s:
        if q.isdigit():
            stmt = select(AdminUser).where(AdminUser.telegram_id == int(q))
        else:
            stmt = select(AdminUser).where(AdminUser.full_name.ilike(f"%{q}%")).limit(limit)
        return list((await s.execute(stmt)).scalars().unique().all())


async def set_admin_active(telegram_id: int, active: bool) -> bool:
    """Back-compat wrapper used by older call sites; prefer activate_admin/disable_admin."""
    return await (activate_admin(telegram_id) if active else disable_admin(telegram_id))
