from app.core import rbac
from app.core.security import has, primary_role


def test_owner_wildcard_grants_most_permissions():
    owner = {rbac.SYSTEM_OWNER}
    assert has(owner, "view_all_orders")
    assert has(owner, "edit_pricing")
    assert has(owner, "manage_admins")


def test_prescription_safety_override_excludes_owner():
    # Hard rule: only pharmacists approve prescriptions — NOT the System Owner.
    assert has({rbac.SYSTEM_OWNER}, "approve_prescription") is False
    assert has({rbac.LEAD_PHARMACIST}, "approve_prescription") is True
    assert has({rbac.PHARMACIST_ADMIN}, "approve_prescription") is True


def test_sales_support_cannot_approve_payment_or_rx():
    s = {rbac.SALES_SUPPORT}
    assert has(s, "message_customer") is True
    assert has(s, "approve_payment") is False
    assert has(s, "approve_prescription") is False
    assert has(s, "edit_pricing") is False


def test_finance_payment_permissions():
    f = {rbac.FINANCE}
    assert has(f, "approve_payment") is True
    assert has(f, "reject_payment") is True
    assert has(f, "approve_prescription") is False
    assert has(f, "edit_pricing") is False


def test_packaging_and_dispatcher_scopes():
    assert has({rbac.PACKAGING}, "start_packaging") is True
    assert has({rbac.PACKAGING}, "approve_payment") is False
    assert has({rbac.DISPATCHER}, "mark_delivered") is True
    assert has({rbac.DISPATCHER}, "view_delivery_address") is True
    assert has({rbac.DISPATCHER}, "edit_pricing") is False


def test_multi_role_union():
    both = {rbac.FINANCE, rbac.PACKAGING}
    assert has(both, "approve_payment") is True
    assert has(both, "start_packaging") is True


def test_primary_role_picks_highest():
    # ROLES is ordered by privilege; primary_role returns the earliest-listed match.
    assert primary_role({rbac.DISPATCHER, rbac.SYSTEM_OWNER}) == rbac.SYSTEM_OWNER
    assert primary_role({rbac.DISPATCHER, rbac.FINANCE}) == rbac.DISPATCHER
    assert primary_role(set()) is None


def test_every_role_has_a_menu():
    for role_key in rbac.ROLES:
        assert rbac.menu_for({role_key}), f"{role_key} has no menu"


def test_menu_merge_dedupes():
    menu = rbac.menu_for({rbac.SYSTEM_OWNER, rbac.FINANCE})
    callbacks = [cb for _, cb in menu]
    assert len(callbacks) == len(set(callbacks))
