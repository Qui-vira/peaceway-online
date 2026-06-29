from app.core.config import Settings
from app.core.security import can, resolve_role
from app.models.ops import StaffRole


def _settings():
    return Settings(
        owner_telegram_ids="100",
        pharmacist_telegram_ids="200",
        dispatcher_telegram_ids="300",
        _env_file=None,
    )


def test_owner_resolves():
    assert resolve_role(100, _settings()) == StaffRole.OWNER


def test_pharmacist_resolves():
    assert resolve_role(200, _settings()) == StaffRole.PHARMACIST


def test_unknown_is_none():
    assert resolve_role(999, _settings()) is None


def test_action_permissions():
    assert can(StaffRole.PHARMACIST, "review_prescription") is True
    assert can(StaffRole.PHARMACIST, "edit_pricing") is False
    assert can(StaffRole.OWNER, "edit_pricing") is True
    assert can(StaffRole.DISPATCHER, "mark_dispatched") is True
    assert can(None, "approve_payment") is False
