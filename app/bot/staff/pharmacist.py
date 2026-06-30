"""Pharmacist Inbox: view and reply to customer medication questions.

Gated on `reply_pharmacist_tickets`. Replies are DM'd to the customer; each
turn is appended to the thread (PharmacistMessage) so the full conversation
history is preserved.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.staff.states import PharmacistFlow
from app.core.db import get_session
from app.core.security import get_role_keys, has, log_activity, primary_role
from app.models import Customer, PharmacistQuestion, Product
from app.services.pharmacist_inbox import add_pharmacist_reply, get_thread

router = Router(name="staff-pharmacist")


async def _guard(event) -> set[str] | None:
    role_keys = await get_role_keys(event.from_user.id)
    if not has(role_keys, "reply_pharmacist_tickets"):
        return None
    return role_keys


@router.callback_query(F.data == "staff:tickets")
async def inbox(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        questions = (
            await session.execute(
                select(PharmacistQuestion)
                .where(PharmacistQuestion.is_answered.is_(False))
                .order_by(PharmacistQuestion.created_at.desc())
                .limit(15)
            )
        ).scalars().all()
    if not questions:
        await call.message.edit_text(
            "📥 Pharmacist Inbox is empty. No open questions.",
            reply_markup=_back_kb(),
        )
        await call.answer()
        return
    kb = InlineKeyboardBuilder()
    for q in questions:
        preview = q.question[:40].replace("\n", " ")
        kb.button(text=f"💬 {preview}", callback_data=f"ptkt:open:{q.id}")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text("📥 <b>Pharmacist Inbox</b>\nOpen questions:", reply_markup=kb.as_markup())
    await call.answer()


def _back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    return kb.as_markup()


@router.callback_query(F.data.startswith("ptkt:open:"))
async def open_ticket(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    qid = UUID(call.data.split("ptkt:open:", 1)[1])
    async with get_session() as session:
        q = await session.get(PharmacistQuestion, qid)
        if q is None:
            await call.answer("Not found.", show_alert=True)
            return
        product = await session.get(Product, q.product_id) if q.product_id else None
        thread = await get_thread(session, qid)

        lines = ["💬 <b>Conversation</b>"]
        if product:
            lines.append(f"Product: <b>{product.name}</b>")
        lines.append("")
        for m in thread:
            when = m.created_at.strftime("%m-%d %H:%M")
            who = "🧑 Customer" if m.sender == "customer" else "👨‍⚕️ Pharmacist"
            lines.append(f"<i>{when}</i> {who}: {m.body}")
        text = "\n".join(lines)

    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Reply", callback_data=f"ptkt:reply:{qid}")
    kb.button(text="⬅️ Back to Inbox", callback_data="staff:tickets")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("ptkt:reply:"))
async def ask_reply(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    qid = call.data.split("ptkt:reply:", 1)[1]
    await state.set_state(PharmacistFlow.reply)
    await state.update_data(question_id=qid)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=f"ptkt:open:{qid}")
    await call.message.edit_text("✍️ Type your reply to the customer:", reply_markup=kb.as_markup())
    await call.answer()


@router.message(PharmacistFlow.reply, F.text)
async def send_reply(message: Message, state: FSMContext) -> None:
    role_keys = await _guard(message)
    if role_keys is None:
        await state.clear()
        return
    data = await state.get_data()
    qid = data.get("question_id")
    await state.clear()
    answer = message.text.strip()
    by = f"{primary_role(role_keys) or 'pharmacist'}:{message.from_user.id}"

    customer_chat = None
    async with get_session() as session:
        q = await session.get(PharmacistQuestion, UUID(qid))
        if q is None:
            await message.answer("Question not found.")
            return
        await add_pharmacist_reply(session, q, message.from_user.id, answer, by)
        customer = await session.get(Customer, q.customer_id)
        customer_chat = customer.telegram_id if customer else None

    await log_activity(message.from_user.id, role_keys, "pharmacist_reply", "pharmacist_question", qid)

    delivered = False
    if customer_chat:
        try:
            await message.bot.send_message(
                customer_chat,
                f"💬 <b>Reply from the pharmacist</b>\n\n{answer}\n\n"
                "If you have more questions, tap Ask the Pharmacist anytime.",
            )
            delivered = True
        except Exception:  # noqa: BLE001
            delivered = False

    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Back to Inbox", callback_data="staff:tickets")
    note = (
        "Reply sent to the customer ✅"
        if delivered
        else "Saved, but the customer couldn't be DM'd (they may need to /start the bot)."
    )
    await message.answer(note, reply_markup=kb.as_markup())
