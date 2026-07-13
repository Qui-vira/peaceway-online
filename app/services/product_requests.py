"""Product-request CRM logic: thread, status timeline, safety-gated conversion.

A product request is treated as a customer lead with a full lifecycle, not a
closed admin task - every status change is recorded and (optionally) shown to
the customer; every message (customer or admin) is recorded in the thread.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProductRequest, ProductRequestMessage, ProductRequestStatusEvent
from app.models.ops import ProductRequestStatus

# Statuses that mean "this medicine is cleared to sell" - only reachable via a
# pharmacist-permission gate when the request is medicine-related.
MEDICINE_CLEARANCE_STATUSES = {ProductRequestStatus.AVAILABLE.value, ProductRequestStatus.READY_TO_ORDER.value}

# Statuses from which "Convert to Order" is allowed.
CONVERTIBLE_STATUSES = {ProductRequestStatus.AVAILABLE.value, ProductRequestStatus.READY_TO_ORDER.value}


def requires_pharmacist_clearance(request: ProductRequest, new_status: str) -> bool:
    """True if setting `new_status` on this request needs a pharmacist permission."""
    return request.is_medicine and new_status in MEDICINE_CLEARANCE_STATUSES


def can_convert_to_order(request: ProductRequest) -> tuple[bool, str | None]:
    """Safety rule: never convert a medicine request straight to an order
    without it having passed pharmacist clearance first."""
    if request.is_medicine and request.status not in CONVERTIBLE_STATUSES:
        return False, (
            "This is a medicine request - a pharmacist must confirm it's "
            "Available or Ready to Order before it can be converted."
        )
    return True, None


async def add_message(
    session: AsyncSession, request: ProductRequest, sender_type: str, body: str,
    sender_admin_id: int | None = None, attachment_file_id: str | None = None,
) -> ProductRequestMessage:
    msg = ProductRequestMessage(
        product_request_id=request.id, sender_type=sender_type, sender_admin_id=sender_admin_id,
        message_text=body, attachment_file_id=attachment_file_id,
    )
    session.add(msg)
    now = datetime.now(timezone.utc)
    if sender_type == "customer":
        request.last_customer_update_at = now
    elif sender_type == "admin":
        request.last_admin_update_at = now
    return msg


async def get_thread(session: AsyncSession, request_id: UUID) -> list[ProductRequestMessage]:
    return list(
        (
            await session.execute(
                select(ProductRequestMessage)
                .where(ProductRequestMessage.product_request_id == request_id)
                .order_by(ProductRequestMessage.created_at)
            )
        ).scalars().all()
    )


async def transition_status(
    session: AsyncSession, request: ProductRequest, new_status: str, admin_telegram_id: int,
    customer_visible_message: str | None = None,
) -> ProductRequestStatusEvent:
    old = request.status
    request.status = new_status
    now = datetime.now(timezone.utc)
    request.last_admin_update_at = now
    if customer_visible_message:
        request.customer_visible_message = customer_visible_message
    if new_status == ProductRequestStatus.CUSTOMER_NOTIFIED.value:
        request.notified_at = now
    if new_status in (ProductRequestStatus.CLOSED.value, ProductRequestStatus.REJECTED.value, ProductRequestStatus.FULFILLED.value):
        request.closed_at = now

    event = ProductRequestStatusEvent(
        product_request_id=request.id, old_status=old, new_status=new_status,
        changed_by_admin_id=admin_telegram_id, customer_visible_message=customer_visible_message,
    )
    session.add(event)
    return event


async def notify_available(bot: Bot, telegram_id: int, request: ProductRequest, price) -> bool:
    text = (
        f"🎉 Good news. <b>{request.product_name}</b> is now available at Peaceway. "
        f"Price: ₦{price:,.0f}. Would you like to order it now?"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Order Now", callback_data=f"preqnotify:order:{request.id}")
    kb.button(text="💬 Ask Pharmacist", callback_data=f"preqnotify:ask:{request.id}")
    kb.button(text="⏭ Not Now", callback_data=f"preqnotify:notnow:{request.id}")
    kb.adjust(1)
    try:
        await bot.send_message(telegram_id, text, reply_markup=kb.as_markup())
        return True
    except Exception:  # noqa: BLE001
        return False


async def notify_not_available(bot: Bot, telegram_id: int, request: ProductRequest) -> bool:
    text = (
        f"😔 Sorry, <b>{request.product_name}</b> is not currently available. "
        "We can keep checking and update you when it becomes available."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🔔 Keep Me Updated", callback_data=f"preqnotify:keepupdated:{request.id}")
    kb.button(text="💬 Ask Pharmacist", callback_data=f"preqnotify:ask:{request.id}")
    kb.button(text="🚫 Cancel Request", callback_data=f"preqnotify:cancel:{request.id}")
    kb.adjust(1)
    try:
        await bot.send_message(telegram_id, text, reply_markup=kb.as_markup())
        return True
    except Exception:  # noqa: BLE001
        return False
