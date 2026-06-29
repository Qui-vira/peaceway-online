"""Staff alerting: Telegram DM + email, with mutual fallback.

Routing:
  - Owner receives all alerts.
  - Pharmacist receives prescription-review alerts.
  - Packaging receives payment-approved (ready-to-pack) alerts.
  - Dispatcher receives ready-for-dispatch alerts.
  - Support receives payment-submitted / customer-help alerts.

If a Telegram DM fails (e.g. staff hasn't /start-ed the bot), the email is still
sent, and vice-versa. Both failures are logged.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import Bot
from sqlalchemy import select

from app.bot.keyboards.staff import order_actions
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import resolve_role
from app.models import Order
from app.models.ops import StaffRole
from app.services.email import send_email

log = get_logger("alerts")

_ROLE_TO_EMAIL_KEY = {
    StaffRole.OWNER: "owner",
    StaffRole.PHARMACIST: "pharmacist",
    StaffRole.PACKAGING: "packaging",
    StaffRole.DISPATCHER: "dispatcher",
    StaffRole.SUPPORT: "support",
}


def order_summary(order: Order) -> str:
    lines = [
        f"🧾 <b>Order {order.code}</b>",
        f"Status: <b>{order.status.value}</b>" + (
            f" | Rx: {order.rx_status.value}" if order.rx_status.value != "NOT_REQUIRED" else ""
        ),
        "",
        f"👤 {order.delivery_name or '-'}  📞 {order.delivery_phone or '-'}",
        f"📍 {order.delivery_address or '-'}, {order.delivery_area or '-'}",
    ]
    if order.delivery_landmark:
        lines.append(f"🏁 {order.delivery_landmark}")
    lines.append("")
    for it in order.items:
        rx = " 💊Rx" if it.requires_prescription else ""
        lines.append(f"• {it.product_name} ×{it.quantity} — ₦{it.line_total:,.0f}{rx}")
    lines.append("")
    lines.append(f"💰 <b>Total: ₦{order.total:,.0f}</b>  ({(order.payment_method.value if order.payment_method else 'unpaid')})")
    return "\n".join(lines)


def _ids_for(role: StaffRole) -> set[int]:
    s = get_settings()
    return {
        StaffRole.OWNER: s.owner_ids,
        StaffRole.PHARMACIST: s.pharmacist_ids,
        StaffRole.PACKAGING: s.packaging_ids,
        StaffRole.DISPATCHER: s.dispatcher_ids,
        StaffRole.SUPPORT: s.support_ids,
    }[role]


async def _dm(bot: Bot, telegram_id: int, text: str, order: Order, role: StaffRole) -> bool:
    try:
        await bot.send_message(telegram_id, text, reply_markup=order_actions(order, role))
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("dm_failed", telegram_id=telegram_id, error=str(exc))
        return False


async def notify_roles(bot: Bot, order: Order, roles: set[StaffRole], header: str) -> None:
    """DM every staff member in the given roles and email their role inboxes."""
    settings = get_settings()
    text = f"{header}\n\n{order_summary(order)}"

    # Owner always included.
    roles = set(roles) | {StaffRole.OWNER}

    dm_targets: set[tuple[int, StaffRole]] = set()
    for role in roles:
        for tid in _ids_for(role):
            dm_targets.add((tid, role))

    dm_ok = False
    for tid, role in dm_targets:
        if await _dm(bot, tid, text, order, role):
            dm_ok = True

    # Email each role's configured inbox (plain text).
    email_targets: list[str] = []
    for role in roles:
        email_targets += settings.emails_for(_ROLE_TO_EMAIL_KEY[role])
    plain = text.replace("<b>", "").replace("</b>", "")
    email_ok = await send_email(sorted(set(email_targets)), f"[{settings.pharmacy_name}] {header} — {order.code}", plain)

    if not dm_ok and not email_ok:
        log.warning("alert_no_delivery", order=order.code, header=header,
                    note="No staff DM reachable and no email sent. Configure staff IDs/SMTP.")


async def _load_order(order_id: UUID) -> Order | None:
    from app.core.db import get_session

    async with get_session() as session:
        return (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()


# ── Event helpers ────────────────────────────────────────────────────────────
async def alert_payment_submitted(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {StaffRole.SUPPORT}, "💳 Payment proof submitted — please verify")


async def alert_payment_approved(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {StaffRole.PACKAGING}, "✅ Payment approved — ready to package")


async def alert_ready_for_dispatch(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {StaffRole.DISPATCHER}, "🚚 Order ready for dispatch")


async def alert_rx_review(bot: Bot, order_id: UUID) -> None:
    order = await _load_order(order_id)
    if order:
        await notify_roles(bot, order, {StaffRole.PHARMACIST}, "💊 Prescription order needs review")
