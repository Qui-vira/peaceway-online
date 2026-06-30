from app.core import rbac
from app.models.admin import AdminStatus
from app.services import rbac_service as r


async def test_new_admin_starts_pending(session):
    admin = await r.add_admin(111, rbac.SALES_SUPPORT, full_name="New Hire", session=session)
    assert admin.status == AdminStatus.PENDING
    assert admin.is_active is False
    # Pending admin has no role keys (no access) despite having a role row.
    keys = await r.get_role_keys(111, session)
    assert keys == set()


async def test_activate_grants_access(session):
    await r.add_admin(222, rbac.PACKAGING, session=session)
    ok = await r.activate_admin(222, session=session)
    assert ok is True
    keys = await r.get_role_keys(222, session)
    assert rbac.PACKAGING in keys


async def test_disable_revokes_access_but_keeps_roles(session):
    await r.add_admin(333, rbac.FINANCE, session=session)
    await r.activate_admin(333, session=session)
    await r.disable_admin(333, session=session)
    keys = await r.get_role_keys(333, session)
    assert keys == set()  # no access while disabled

    # reactivating restores the role without re-adding it
    await r.activate_admin(333, session=session)
    keys = await r.get_role_keys(333, session)
    assert rbac.FINANCE in keys


async def test_remove_clears_roles_and_access(session):
    await r.add_admin(444, rbac.DISPATCHER, session=session)
    await r.activate_admin(444, session=session)
    await r.remove_admin(444, session=session)
    keys = await r.get_role_keys(444, session)
    assert keys == set()

    # re-adding a removed admin starts them fresh at PENDING
    admin = await r.add_admin(444, rbac.DISPATCHER, session=session)
    assert admin.status == AdminStatus.PENDING


async def test_remove_single_role_keeps_others(session):
    await r.add_admin(555, rbac.SALES_SUPPORT, session=session)
    await r.add_admin(555, rbac.COMMUNITY_MANAGER, session=session)
    await r.activate_admin(555, session=session)
    await r.remove_admin_role(555, rbac.SALES_SUPPORT, session=session)
    keys = await r.get_role_keys(555, session)
    assert keys == {rbac.COMMUNITY_MANAGER}


async def test_search_by_telegram_id_and_name(session):
    await r.add_admin(666, rbac.FINANCE, full_name="Jane Finance", session=session)
    by_id = await r.search_admins("666", session=session)
    by_name = await r.search_admins("jane", session=session)
    assert {a.telegram_id for a in by_id} == {666}
    assert {a.telegram_id for a in by_name} == {666}


async def test_disabled_admin_excluded_from_alert_recipients(session):
    """Regression: recipients_for_roles must keep filtering on is_active."""
    await r.add_admin(777, rbac.LEAD_PHARMACIST, session=session)
    await r.activate_admin(777, session=session)
    ids, _ = await r.recipients_for_roles({rbac.LEAD_PHARMACIST}, session=session)
    assert 777 in ids

    await r.disable_admin(777, session=session)
    ids, _ = await r.recipients_for_roles({rbac.LEAD_PHARMACIST}, session=session)
    assert 777 not in ids
