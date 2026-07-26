"""Unit tests for the Gate-1 write-path (SQLite, no triggers needed)."""
from __future__ import annotations

from sqlalchemy import select

from app.models import AdminUser, Customer, Order, PrescriptionVerification
from app.models.admin import AdminStatus
from app.models.orders import OrderStatus, RxStatus
from app.services import verification as verification_svc
from app.services.rbac_service import get_admin_id


async def test_get_admin_id_resolves_only_active_admin(db_session):
    a = AdminUser(telegram_id=555, full_name="Ph", is_active=True, status=AdminStatus.ACTIVE)
    db_session.add(a)
    await db_session.flush()

    assert await get_admin_id(555, db_session) == a.id
    assert await get_admin_id(999, db_session) is None  # unknown telegram id

    a.is_active = False  # deactivated -> no longer resolves
    await db_session.flush()
    assert await get_admin_id(555, db_session) is None


async def test_record_verification_inserts_attributed_row(db_session):
    cust = Customer(full_name="C")
    admin = AdminUser(telegram_id=1, full_name="Ph", is_active=True, status=AdminStatus.ACTIVE)
    db_session.add_all([cust, admin])
    await db_session.flush()
    order = Order(
        code="PW-V1", customer_id=cust.id,
        status=OrderStatus.AWAITING_PAYMENT, rx_status=RxStatus.APPROVED_FOR_PAYMENT,
    )
    db_session.add(order)
    await db_session.flush()

    row = await verification_svc.record_verification(
        db_session, order_id=order.id, pharmacist_admin_id=admin.id,
        decision=verification_svc.APPROVED,
    )
    assert row.decision == "APPROVED"
    assert row.verified_at is not None  # required for the Gate-1 trigger to honour it

    got = (
        await db_session.execute(
            select(PrescriptionVerification).where(PrescriptionVerification.order_id == order.id)
        )
    ).scalar_one()
    assert got.pharmacist_user_id == admin.id
