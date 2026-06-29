"""Staff role resolution and access gating, driven by env-configured Telegram IDs."""
from __future__ import annotations

from app.core.config import Settings, get_settings
from app.models.ops import StaffRole


def resolve_role(telegram_id: int, settings: Settings | None = None) -> StaffRole | None:
    """Return the highest-privilege role for a Telegram user, or None if not staff."""
    s = settings or get_settings()
    if telegram_id in s.owner_ids:
        return StaffRole.OWNER
    if telegram_id in s.pharmacist_ids:
        return StaffRole.PHARMACIST
    if telegram_id in s.packaging_ids:
        return StaffRole.PACKAGING
    if telegram_id in s.dispatcher_ids:
        return StaffRole.DISPATCHER
    if telegram_id in s.support_ids:
        return StaffRole.SUPPORT
    return None


def is_staff(telegram_id: int, settings: Settings | None = None) -> bool:
    return resolve_role(telegram_id, settings) is not None


# Which roles may perform each staff action.
ACTION_ROLES: dict[str, set[StaffRole]] = {
    "approve_payment": {StaffRole.OWNER, StaffRole.SUPPORT},
    "reject_payment": {StaffRole.OWNER, StaffRole.SUPPORT},
    "start_packaging": {StaffRole.OWNER, StaffRole.PACKAGING},
    "ready_for_dispatch": {StaffRole.OWNER, StaffRole.PACKAGING},
    "assign_rider": {StaffRole.OWNER, StaffRole.DISPATCHER},
    "mark_dispatched": {StaffRole.OWNER, StaffRole.DISPATCHER},
    "mark_delivered": {StaffRole.OWNER, StaffRole.DISPATCHER},
    "cancel_order": {StaffRole.OWNER},
    "message_customer": {StaffRole.OWNER, StaffRole.SUPPORT, StaffRole.DISPATCHER},
    "review_prescription": {StaffRole.OWNER, StaffRole.PHARMACIST},
    "edit_pricing": {StaffRole.OWNER},
}


def can(role: StaffRole | None, action: str) -> bool:
    if role is None:
        return False
    return role in ACTION_ROLES.get(action, set())
