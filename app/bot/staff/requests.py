"""Admin view of customer product/supplement requests."""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core.db import get_session
from app.core.security import get_role_keys, has, log_activity
from app.models import Customer, ProductRequest

router = Router(name="staff-requests")


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "view_product_requests"):
        await call.answer("Not authorised.", show_alert=True)
        return None
    return role_keys


@router.callback_query(F.data == "staff:requests")
async def list_requests(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    async with get_session() as session:
        rows = (
            await session.execute(
                select(ProductRequest)
                .where(ProductRequest.status == "NEW")
                .order_by(ProductRequest.created_at.desc())
                .limit(15)
            )
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.button(text=f"📝 {r.product_name[:40]}", callback_data=f"preqadm:open:{r.id}")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    text = "📝 <b>Product Requests</b>" if rows else "📝 No open product requests."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("preqadm:open:"))
async def open_request(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    rid = UUID(call.data.split("preqadm:open:", 1)[1])
    async with get_session() as session:
        req = await session.get(ProductRequest, rid)
        if req is None:
            await call.answer("Not found.", show_alert=True)
            return
        customer = await session.get(Customer, req.customer_id)
        text = (
            f"📝 <b>{req.product_name}</b>\n"
            + (f"Strength: {req.strength}\n" if req.strength else "")
            + (f"Form: {req.form}\n" if req.form else "")
            + (f"Qty: {req.quantity}\n" if req.quantity else "")
            + (f"Note: {req.note}\n" if req.note else "")
            + f"Area: {req.delivery_area}\n"
            f"Customer: {customer.full_name if customer else '-'} "
            f"(id {customer.telegram_id if customer else '-'})\n"
            f"Status: {req.status}"
        )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Mark Fulfilled", callback_data=f"preqadm:fulfil:{rid}")
    kb.button(text="❌ Reject", callback_data=f"preqadm:reject:{rid}")
    kb.button(text="⬅️ Back", callback_data="staff:requests")
    kb.adjust(2, 1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


async def _set_status(call: CallbackQuery, rid: UUID, status: str) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    async with get_session() as session:
        req = await session.get(ProductRequest, rid)
        if req is None:
            await call.answer("Not found.", show_alert=True)
            return
        req.status = status
    await log_activity(
        call.from_user.id, role_keys, "product_request_status", "product_request", str(rid), {"status": status}
    )
    await call.answer("Updated ✅")
    await list_requests(call)


@router.callback_query(F.data.startswith("preqadm:fulfil:"))
async def fulfil(call: CallbackQuery) -> None:
    await _set_status(call, UUID(call.data.split("preqadm:fulfil:", 1)[1]), "FULFILLED")


@router.callback_query(F.data.startswith("preqadm:reject:"))
async def reject(call: CallbackQuery) -> None:
    await _set_status(call, UUID(call.data.split("preqadm:reject:", 1)[1]), "REJECTED")
