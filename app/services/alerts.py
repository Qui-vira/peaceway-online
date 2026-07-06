"""Staff alerting: Telegram DM + email, with mutual fallback (RBAC-driven).

Recipients are resolved from the DB (admin_users + assignments) by role. The
System Owner always receives alerts. DM failure still sends email and vice-versa.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import Bot
from sqlalchemy import select

from app.core import rbac
from app.core.logging import get_logger
from app.models import Order
from app.services.email import send_email
from app.services.rbac_service import get_role_keys, recipients_for_roles

log = get_logger("alerts")


def order_summary(order: Order, include_contact: bool = True) -> str:
    lines = [
        f"🧾 <b>Order {order.code}</b>",
        f"Status: <b>{order.status.value}</b>" + (
            f" | Rx: {order.rx_status.value}" if order.rx_status.value != "NOT_REQUIRED" else ""
        ),
        "",
    ]
    if include_contact:
        lines.append(f"👤 {order.delivery_name or '-'}  📞 {order.delivery_phone or '-'}")
        lines.append(f"📍 {order.delivery_address or '-'}, {order.delivery_area or '-'}")
        if order.delivery_landmark:
            lines.append(f"🏁 {order.delivery_landmark}")
    else:
        # Privacy: hide personal contact details from roles that don't need them.
        lines.append(f"📍 Area: {order.delivery_area or '-'}")
    lines.append("")
    if order.sourcing:
        lines.append(f"Fulfilment: <b>{order.sourcing.fulfillment_status.value}</b>")
        if order.sourcing.customer_facing_status:
            lines.append(order.sourcing.customer_facing_status)
        if order.sourcing.pickup_code:
            lines.append(f"Pickup code: <code>{order.sourcing.pickup_code}</code>")
        lines.append("")
    for it in order.items:
        rx = " 💊Rx" if it.requires_prescription else ""
        lines.append(f"• {it.product_name} ×{it.quantity} · ₦{it.line_total:,.0f}{rx}")
    lines.append("")
    method = order.payment_method.value if order.payment_method else "unpaid"
    lines.append(f"💰 <b>Total: ₦{order.total:,.0f}</b>  ({method})")
    return "\n".join(lines)


async def notify_roles(bot: Bot, order: Order, roles: set[str], header: str) -> None:
    """DM every active admin in the target roles (System Owner always) + email them."""
    target = set(roles) | {rbac.SYSTEM_OWNER}
    telegram_ids, emails = await recipients_for_roles(target)

    from app.bot.keyboards.staff import order_actions

    text = f"{header}\n\n{order_summary(order)}"
    dm_ok = False
    for tid in telegram_ids:
        try:
            tid_roles = await get_role_keys(tid)
            await bot.send_message(tid, text, reply_markup=order_actions(order, tid_roles))
            dm_ok = True
        except Exception as exc:  # noqa: BLE001
            log.error("dm_failed", telegram_id=tid, error=str(exc))

    plain = text.replace("<b>", "").replace("</b>", "")
    from app.core.config import get_settings

    email_ok = await send_email(emails, f"[{get_settings().pharmacy_name}] {header}: {order.code}", plain)

    if not dm_ok and not email_ok:
        log.warning("alert_no_delivery", order=order.code, header=header,
                    note="No staff DM reachable and no email sent. Add admins / SMTP.")


async def _load_order(order_id: UUID) -> Order | None:
    from app.core.db import get_session

    async with get_session() as session:
        return (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()


# ── Event helpers ────────────────────────────────────────────────────────────
async def alert_payment_submitted(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {rbac.FINANCE, rbac.SALES_SUPPORT}, "💳 Payment proof submitted, please verify")


async def alert_payment_approved(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {rbac.PACKAGING}, "✅ Payment approved, ready to package")


async def alert_ready_for_dispatch(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {rbac.DISPATCHER}, "🚚 Order ready for dispatch")


async def alert_rx_review(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {rbac.LEAD_PHARMACIST, rbac.PHARMACIST_ADMIN}, "💊 Prescription order needs review")


async def alert_sourcing_requested(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(
            bot,
            order,
            {rbac.SYSTEM_OWNER, rbac.SALES_SUPPORT},
            "📡 Out-of-stock order needs approved-network sourcing",
        )
