"""Pharmacist review of uploaded prescriptions: list, view file, approve/reject."""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core.db import get_session
from app.core.security import get_role_keys, has, log_activity, primary_role
from app.models import Customer, Prescription, Product

router = Router(name="staff-prescriptions")


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "review_prescriptions"):
        await call.answer("Not authorised.", show_alert=True)
        return None
    return role_keys


@router.callback_query(F.data == "staff:prescriptions")
async def list_pending(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    async with get_session() as session:
        rows = (
            await session.execute(
                select(Prescription)
                .where(Prescription.review_status == "PENDING")
                .order_by(Prescription.created_at.desc())
                .limit(15)
            )
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    for r in rows:
        when = r.created_at.strftime("%m-%d %H:%M")
        kb.button(text=f"📄 {when} ({r.file_type})", callback_data=f"presc:open:{r.id}")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    text = "📄 <b>Pending Prescriptions</b>" if rows else "📄 No pending prescriptions."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("presc:open:"))
async def open_prescription(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    pid = UUID(call.data.split("presc:open:", 1)[1])
    async with get_session() as session:
        presc = await session.get(Prescription, pid)
        if presc is None:
            await call.answer("Not found.", show_alert=True)
            return
        customer = await session.get(Customer, presc.customer_id)
        product = await session.get(Product, presc.product_id) if presc.product_id else None
        file_id, file_type, status = presc.file_id, presc.file_type, presc.review_status
        cust_name = customer.full_name if customer else "customer"
        product_name = product.name if product else None

    caption = (
        f"📄 Prescription from {cust_name}\n"
        + (f"For: {product_name}\n" if product_name else "")
        + f"Status: {status}"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Approve", callback_data=f"presc:approve:{pid}")
    kb.button(text="❌ Reject", callback_data=f"presc:reject:{pid}")
    kb.button(text="⬅️ Back", callback_data="staff:prescriptions")
    kb.adjust(2, 1)

    try:
        if file_type == "image":
            await call.message.answer_photo(file_id, caption=caption, reply_markup=kb.as_markup())
        else:
            await call.message.answer_document(file_id, caption=caption, reply_markup=kb.as_markup())
    except Exception:  # noqa: BLE001
        await call.message.answer(caption + "\n\n(Could not load the file preview.)", reply_markup=kb.as_markup())
    await call.answer()


async def _decide(call: CallbackQuery, pid: UUID, approve: bool) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    by = f"{primary_role(role_keys) or 'pharmacist'}:{call.from_user.id}"
    customer_chat = None
    async with get_session() as session:
        presc = await session.get(Prescription, pid)
        if presc is None:
            await call.answer("Not found.", show_alert=True)
            return
        presc.review_status = "APPROVED" if approve else "REJECTED"
        presc.reviewed_by = by
        customer = await session.get(Customer, presc.customer_id)
        customer_chat = customer.telegram_id if customer else None

    await log_activity(call.from_user.id, role_keys, "prescription_decision", "prescription", str(pid),
                        {"approved": approve})

    if customer_chat:
        msg = (
            "✅ Your prescription has been approved. You can proceed to order the medicine."
            if approve
            else "⛔ Your prescription could not be approved. Please contact our pharmacist for guidance."
        )
        try:
            await call.bot.send_message(customer_chat, msg)
        except Exception:  # noqa: BLE001
            pass

    await call.message.answer("✅ Decision recorded." if approve else "❌ Decision recorded.")
    await call.answer("Done ✅")


@router.callback_query(F.data.startswith("presc:approve:"))
async def approve(call: CallbackQuery) -> None:
    await _decide(call, UUID(call.data.split("presc:approve:", 1)[1]), approve=True)


@router.callback_query(F.data.startswith("presc:reject:"))
async def reject(call: CallbackQuery) -> None:
    await _decide(call, UUID(call.data.split("presc:reject:", 1)[1]), approve=False)
