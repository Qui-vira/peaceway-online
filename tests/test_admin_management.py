from app.core import rbac
from app.models.admin import AdminStatus
from app.services import rbac_service as r


async def test_new_admin_starts_pending(db_session):
    admin = await r.add_admin(111, rbac.SALES_SUPPORT, full_name="New Hire", session=db_session)
    assert admin.status == AdminStatus.PENDING
    assert admin.is_active is False
    # Pending admin has no role keys (no access) despite having a role row.
    keys = await r.get_role_keys(111, db_session)
    assert keys == set()


async def test_activate_grants_access(db_session):
    await r.add_admin(222, rbac.PACKAGING, session=db_session)
    ok = await r.activate_admin(222, session=db_session)
    assert ok is True
    keys = await r.get_role_keys(222, db_session)
    assert rbac.PACKAGING in keys


async def test_disable_revokes_access_but_keeps_roles(db_session):
    await r.add_admin(333, rbac.FINANCE, session=db_session)
    await r.activate_admin(333, session=db_session)
    await r.disable_admin(333, session=db_session)
    keys = await r.get_role_keys(333, db_session)
    assert keys == set()  # no access while disabled

    # reactivating restores the role without re-adding it
    await r.activate_admin(333, session=db_session)
    keys = await r.get_role_keys(333, db_session)
    assert rbac.FINANCE in keys


async def test_remove_clears_roles_and_access(db_session):
    await r.add_admin(444, rbac.DISPATCHER, session=db_session)
    await r.activate_admin(444, session=db_session)
    await r.remove_admin(444, session=db_session)
    keys = await r.get_role_keys(444, db_session)
    assert keys == set()

    # re-adding a removed admin starts them fresh at PENDING
    admin = await r.add_admin(444, rbac.DISPATCHER, session=db_session)
    assert admin.status == AdminStatus.PENDING


async def test_remove_single_role_keeps_others(db_session):
    await r.add_admin(555, rbac.SALES_SUPPORT, session=db_session)
    await r.add_admin(555, rbac.COMMUNITY_MANAGER, session=db_session)
    await r.activate_admin(555, session=db_session)
    await r.remove_admin_role(555, rbac.SALES_SUPPORT, session=db_session)
    keys = await r.get_role_keys(555, db_session)
    assert keys == {rbac.COMMUNITY_MANAGER}


async def test_search_by_telegram_id_and_name(db_session):
    await r.add_admin(666, rbac.FINANCE, full_name="Jane Finance", session=db_session)
    by_id = await r.search_admins("666", session=db_session)
    by_name = await r.search_admins("jane", session=db_session)
    assert {a.telegram_id for a in by_id} == {666}
    assert {a.telegram_id for a in by_name} == {666}


async def test_email_only_admin_can_be_created_and_found(db_session):
    # Email-only staff admins (e.g. web-first finance/ops users) are still valid.
    # Partners are NOT admins any more — they live in the separate partner portal.
    admin = await r.add_admin(None, rbac.FINANCE, full_name="Fin Ops", email="finance@example.com", session=db_session)
    assert admin.telegram_id is None
    assert admin.email == "finance@example.com"

    by_email = await r.search_admins("finance@example.com", session=db_session)
    assert [a.email for a in by_email] == ["finance@example.com"]


async def test_disabled_admin_excluded_from_alert_recipients(db_session):
    """Regression: recipients_for_roles must keep filtering on is_active."""
    await r.add_admin(777, rbac.LEAD_PHARMACIST, session=db_session)
    await r.activate_admin(777, session=db_session)
    ids, _ = await r.recipients_for_roles({rbac.LEAD_PHARMACIST}, session=db_session)
    assert 777 in ids

    await r.disable_admin(777, session=db_session)
    ids, _ = await r.recipients_for_roles({rbac.LEAD_PHARMACIST}, session=db_session)
    assert 777 not in ids
