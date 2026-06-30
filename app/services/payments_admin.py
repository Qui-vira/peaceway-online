"""Payment approval/rejection logic shared by the order action buttons
(app/bot/staff/orders.py act:pay_approve/act:pay_reject) and the dedicated
Payments Review admin (app/bot/staff/payments_admin.py), so there is exactly
one place that decides what "approved" / "rejected" means for a payment.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeliveryStatus, Order, OrderStatus, Payment, PaymentStatus, RxStatus
from app.services import orders as orders_svc


def rx_blocks_payment(order: Order) -> bool:
    """True if this order's prescription items haven't been pharmacist-cleared
    yet — payment approval must never move ahead of that clearance."""
    return order.rx_status not in (RxStatus.NOT_REQUIRED, RxStatus.APPROVED_FOR_PAYMENT)


async def latest_pending_payment(session: AsyncSession, order_id) -> Payment | None:
    return (
        await session.execute(
            select(Payment)
            .where(Payment.order_id == order_id, Payment.status == PaymentStatus.PENDING)
            .order_by(Payment.created_at.desc())
        )
    ).scalars().first()


async def approve_payment(
    session: AsyncSession, order: Order, payment: Payment | None, by_label: str
) -> tuple[bool, str | None]:
    """Approve a payment + advance the order. Returns (ok, error_message)."""
    if rx_blocks_payment(order):
        return False, (
            "This order has prescription items not yet cleared by a pharmacist. "
            "Approval blocked."
        )
    if payment is not None:
        payment.status = PaymentStatus.APPROVED
        payment.verified_by = by_label

    await orders_svc.transition_status(session, order, OrderStatus.PAYMENT_APPROVED, by_label)
    # Automation: OTC orders skip straight to packaging. Rx orders stop at
    # PAYMENT_APPROVED and require a manual "Start Packaging" — preserves the
    # original act:pay_approve checkpoint for medicine orders.
    if order.rx_status == RxStatus.NOT_REQUIRED:
        await orders_svc.transition_status(session, order, OrderStatus.PROCESSING, "system", "Auto: OTC paid")
        await orders_svc.transition_delivery(session, order, DeliveryStatus.PACKAGING, "system")
    return True, None


async def reject_payment(
    session: AsyncSession, order: Order, payment: Payment | None, by_label: str, reason: str | None = None
) -> None:
    if payment is not None:
        payment.status = PaymentStatus.REJECTED
        payment.verified_by = by_label
        if reason:
            payment.note = reason
    await orders_svc.transition_status(session, order, OrderStatus.REJECTED, by_label, reason or "Payment rejected")
