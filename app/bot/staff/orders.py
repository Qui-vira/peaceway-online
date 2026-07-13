"""Staff order-action handlers (role-gated), with automation + audit + customer updates."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.text_decorations import html_decoration
from sqlalchemy import select

from app.bot.staff.states import StaffFlow
from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has, log_activity, primary_role, touch_activity
from app.models import (
    AuditLog,
    Customer,
    DeliveryStatus,
    FulfillmentStatus,
    Order,
    OrderStatus,
    RiderAssignment,
    RxStatus,
)
from app.services import orders as orders_svc
from app.services import payments_admin as payments_admin_svc
from app.services import sourcing as sourcing_svc

router = Router(name="staff-orders")
log = get_logger("staff-orders")

# callback action -> permission key in security.ACTION_ROLES
_ACTION_PERM = {
    "pay_approve": "approve_payment",
    "pay_reject": "reject_payment",
    "packaging": "start_packaging",
    "ready": "ready_for_dispatch",
    "assign": "assign_rider",
    "dispatched": "mark_dispatched",
    "delivered": "mark_delivered",
    "cancel": "cancel_order",
    "msg": "message_customer",
    "partner_confirmed": "view_all_orders",
    "partner_rejected": "view_all_orders",
    "pack_ready": "ready_for_dispatch",
    "dispatch_assigned": "assign_rider",
    "picked_up": "mark_dispatched",
    "rx_approve": "approve_prescription",
    "rx_reject": "approve_prescription",
}


async def _notify_customer(bot: Bot, order: Order, text: str) -> bool:
    """Send a message to the order's customer. Returns True only if delivered.

    A None telegram_id (web-only customer) or a Telegram send failure (blocked
    bot, bad parse) both return False so callers can tell staff it did not send.
    """
    async with get_session() as session:
        customer = await session.get(Customer, order.customer_id)
    if not customer or customer.telegram_id is None:
        return False
    try:
        await bot.send_message(customer.telegram_id, text)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("notify_customer_failed", order=order.code, error=str(exc))
        return False


async def _audit(session, call: CallbackQuery, role_keys: set[str], action: str, code: str) -> None:
    session.add(
        AuditLog(
            actor_telegram_id=call.from_user.id,
            actor_role=",".join(sorted(role_keys)) if role_keys else None,
            action=action,
            entity="order",
            entity_id=code,
        )
    )


async def _refresh(call: CallbackQuery, code: str, role_keys: set[str]) -> None:
    from app.bot.keyboards.staff import order_actions
    from app.services.alerts import order_summary

    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order:
            await call.message.edit_text(order_summary(order), reply_markup=order_actions(order, role_keys))


@router.callback_query(F.data.startswith("act:"))
async def handle_action(call: CallbackQuery, state: FSMContext) -> None:
    _, action, code = call.data.split(":", 2)
    role_keys = await get_role_keys(call.from_user.id)
    perm = _ACTION_PERM.get(action)
    if perm is None or not has(role_keys, perm):
        await call.answer("Not authorised for this action.", show_alert=True)
        return
    await touch_activity(call.from_user.id)

    # Interactive actions delegate to FSM capture.
    if action == "assign":
        await state.set_state(StaffFlow.assign_rider)
        await state.update_data(order_code=code)
        await call.message.answer(f"🛵 Send rider details for {code} as: <i>Name, Phone</i>")
        await call.answer()
        return
    if action == "msg":
        await state.set_state(StaffFlow.message_customer)
        await state.update_data(order_code=code)
        await call.message.answer(f"💬 Type the message to send the customer for {code}:")
        await call.answer()
        return

    bot = call.bot
    downstream = None
    customer_msg = None

    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        by = f"{primary_role(role_keys) or 'staff'}:{call.from_user.id}"

        if action == "pay_approve":
            payment = await payments_admin_svc.latest_pending_payment(session, order.id)
            ok, err = await payments_admin_svc.approve_payment(session, order, payment, by)
            if not ok:
                await call.answer(err, show_alert=True)
                return
            customer_msg = f"✅ Payment approved for {code}. We're preparing your order."
            downstream = ("packaging", order.id)

        elif action == "pay_reject":
            payment = await payments_admin_svc.latest_pending_payment(session, order.id)
            await payments_admin_svc.reject_payment(session, order, payment, by)
            customer_msg = f"❌ Payment for {code} could not be verified. Please contact support."

        elif action == "packaging":
            await orders_svc.transition_status(session, order, OrderStatus.PROCESSING, by)
            await orders_svc.transition_delivery(session, order, DeliveryStatus.PACKAGING, by)
            customer_msg = f"📦 Your order {code} is being packaged."

        elif action == "ready":
            await orders_svc.transition_delivery(session, order, DeliveryStatus.READY_FOR_DISPATCH, by)
            downstream = ("dispatch", order.id)

        elif action == "partner_confirmed":
            total_qty = sum(item.quantity for item in order.items)
            await sourcing_svc.confirm_partner(
                session,
                order=order,
                confirmed_quantity=total_qty,
                confirmed_price=order.total,
                expiry_or_batch_confirmation="Pending detailed batch verification",
                ready_for_pickup_at=None,
                confirmed_items=[
                    {
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                    }
                    for item in order.items
                ],
                by=by,
                note="Staff confirmed approved-network fulfilment.",
            )
            customer_msg = (
                f"✅ Your order {code} has been confirmed by Peaceway's approved fulfilment network. "
                "We will update you again once the package is ready for pickup."
            )

        elif action == "partner_rejected":
            await sourcing_svc.reject_partner(
                session,
                order=order,
                reason="Approved partner could not confirm this request yet.",
                by=by,
            )
            customer_msg = (
                f"⚠️ Your order {code} is still under Peaceway review. "
                "We have not confirmed a sourcing partner yet, so we are not promising a delivery ETA."
            )

        elif action == "pack_ready":
            sourcing = await sourcing_svc.mark_pack_ready(
                session,
                order=order,
                pack_verification_photo="staff-confirmed",
                pickup_code=None,
                by=by,
            )
            customer_msg = (
                f"📦 Your order {code} has been packed by an approved partner and verified by Peaceway. "
                f"Pickup code: {sourcing.pickup_code}."
            )

        elif action == "dispatch_assigned":
            await sourcing_svc.mark_dispatch_assigned(session, order=order, by=by)
            customer_msg = f"🛵 Dispatch has been assigned for your order {code}."

        elif action == "picked_up":
            await sourcing_svc.mark_picked_up(
                session,
                order=order,
                pickup_proof="staff-confirmed",
                by=by,
            )
            await orders_svc.transition_delivery(session, order, DeliveryStatus.PICKED_UP, by)
            customer_msg = f"📦 Your order {code} has been picked up and is now under Peaceway tracking."

        elif action == "dispatched":
            await orders_svc.transition_status(session, order, OrderStatus.DISPATCHED, by)
            await orders_svc.transition_delivery(session, order, DeliveryStatus.IN_TRANSIT, by)
            customer_msg = f"🚚 Your order {code} has been dispatched and is on the way!"

        elif action == "delivered":
            await orders_svc.transition_status(session, order, OrderStatus.DELIVERED, by)
            await orders_svc.transition_delivery(session, order, DeliveryStatus.DELIVERED, by)
            if order.sourcing and order.sourcing.fulfillment_status in (
                FulfillmentStatus.PICKED_UP,
                FulfillmentStatus.DISPATCH_ASSIGNED,
                FulfillmentStatus.PACK_READY,
                FulfillmentStatus.PARTNER_CONFIRMED,
            ):
                await sourcing_svc.mark_delivered(
                    session,
                    order=order,
                    delivery_proof="staff-confirmed",
                    by=by,
                )
            customer_msg = f"🏁 Your order {code} has been delivered. Thank you for choosing us!"
            downstream = ("followup", order.id)

        elif action == "cancel":
            await orders_svc.transition_status(session, order, OrderStatus.CANCELLED, by)
            customer_msg = f"🚫 Your order {code} has been cancelled. Contact support for help."

        elif action == "rx_approve":
            await orders_svc.transition_rx(session, order, RxStatus.APPROVED_FOR_PAYMENT, by)
            await orders_svc.transition_status(session, order, OrderStatus.AWAITING_PAYMENT, by)
            customer_msg = f"✅ Your prescription for {code} was approved. You can now pay."

        elif action == "rx_reject":
            await orders_svc.transition_rx(session, order, RxStatus.REJECTED_BY_PHARMACIST, by)
            await orders_svc.transition_status(session, order, OrderStatus.REJECTED, by)
            customer_msg = f"⛔ Your prescription order {code} was not approved. Please contact our pharmacist."

        await _audit(session, call, role_keys, action, code)
        order_snapshot = order

    if customer_msg:
        await _notify_customer(bot, order_snapshot, customer_msg)

    # Fire downstream staff alerts.
    if downstream:
        kind, oid = downstream
        try:
            if kind == "packaging":
                from app.services.alerts import alert_payment_approved

                await alert_payment_approved(bot, oid)
            elif kind == "dispatch":
                from app.services.alerts import alert_ready_for_dispatch

                await alert_ready_for_dispatch(bot, oid)
            elif kind == "followup":
                from app.scheduler.jobs import schedule_followup

                schedule_followup(bot, oid)
        except Exception as exc:  # noqa: BLE001
            log.error("downstream_alert_failed", kind=kind, error=str(exc))

    await _refresh(call, code, role_keys)
    await call.answer("Done ✅")


@router.message(StaffFlow.assign_rider, F.text)
async def capture_rider(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    code = data.get("order_code")
    await state.clear()
    parts = [p.strip() for p in message.text.split(",", 1)]
    rider_name = parts[0]
    rider_phone = parts[1] if len(parts) > 1 else None

    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await message.answer("Order not found.")
            return
        session.add(
            RiderAssignment(order_id=order.id, rider_name=rider_name, rider_phone=rider_phone, is_manual=True)
        )
        await orders_svc.transition_delivery(session, order, DeliveryStatus.RIDER_ASSIGNED, f"manual:{message.from_user.id}")
        if order.sourcing and order.sourcing.sourcing_required:
            await sourcing_svc.mark_dispatch_assigned(session, order=order, by=f"manual:{message.from_user.id}")
        order_snapshot = order
    await _notify_customer(
        message.bot, order_snapshot, f"🛵 A rider has been assigned to your order {code}."
    )
    await message.answer(f"✅ Rider {rider_name} assigned to {code}.")


@router.message(StaffFlow.message_customer, F.text)
async def capture_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    code = data.get("order_code")
    await state.clear()
    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await message.answer("Order not found.")
            return
        order_snapshot = order
    safe_text = html_decoration.quote(message.text)
    sent = await _notify_customer(
        message.bot, order_snapshot, f"💬 Message from {get_pharmacy_name()} about {code}:\n\n{safe_text}"
    )
    if sent:
        await message.answer("✅ Message sent to customer.")
    else:
        await message.answer(
            "⚠️ Could not deliver the message - the customer may have no Telegram "
            "account linked or has blocked the bot. Try another channel."
        )


def get_pharmacy_name() -> str:
    from app.core.config import get_settings

    return get_settings().pharmacy_name
