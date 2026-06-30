"""Ask-the-Pharmacist flow (collects a question, alerts pharmacist, no medical advice)."""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.customer.states import AskFlow
from app.bot.keyboards.customer import back_cancel, back_to_menu
from app.core import rbac
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import Product
from app.services.customers import get_or_create_customer
from app.services.email import send_email
from app.services.pharmacist_inbox import add_customer_message
from app.services.rbac_service import recipients_for_roles

router = Router(name="customer-support")
log = get_logger("support")

SAFETY = (
    "⚠️ I can pass your question to our pharmacist, but I can't give a diagnosis or "
    "emergency medical advice. For serious symptoms, please see a pharmacist in person "
    "or seek urgent medical care."
)


async def _render_ask(call: CallbackQuery, state: FSMContext, product_id: str | None, origin: str) -> None:
    await state.set_state(AskFlow.waiting_question)
    await state.update_data(ask_product_id=product_id, ask_origin=origin)
    await call.message.edit_text(
        f"💬 <b>Ask the Pharmacist</b>\n\n{SAFETY}\n\nType your question below:",
        reply_markup=back_cancel(origin),
    )
    await call.answer()


async def _start(call: CallbackQuery, state: FSMContext, product_id: str | None, origin: str) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(
        call, state, source="pharmacist",
        resume=lambda: _render_ask(call, state, product_id, origin),
    ):
        return
    await _render_ask(call, state, product_id, origin)


@router.callback_query(F.data == "menu:ask")
async def ask_start(call: CallbackQuery, state: FSMContext) -> None:
    await _start(call, state, product_id=None, origin="menu:home")


@router.callback_query(F.data.startswith("askp:"))
async def ask_start_for_product(call: CallbackQuery, state: FSMContext) -> None:
    product_id = call.data.split("askp:", 1)[1]
    await _start(call, state, product_id=product_id, origin=f"prod:{product_id}")


@router.message(AskFlow.waiting_question, F.text)
async def ask_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = data.get("ask_product_id")
    await state.clear()
    text = message.text.strip()

    async with get_session() as session:
        customer = await get_or_create_customer(session, message.from_user.id, message.from_user.full_name)

        product_name = None
        pid = UUID(product_id) if product_id else None
        if pid:
            p = await session.get(Product, pid)
            product_name = p.name if p else None

        ticket, created = await add_customer_message(
            session, customer.id, message.from_user.id, text, product_id=pid
        )
        cust_name = customer.full_name

    try:
        await _alert_pharmacist(message.bot, cust_name, message.from_user.id, text, product_name)
    except Exception as exc:  # noqa: BLE001
        log.error("ask_alert_failed", error=str(exc))

    note = "Our pharmacist has received your question" if created else "Your message has been added to your open ticket"
    await message.answer(
        f"✅ Thank you. {note} and will reply soon.",
        reply_markup=back_to_menu(),
    )


async def _alert_pharmacist(bot, cust_name, cust_id, text: str, product_name: str | None) -> None:
    telegram_ids, emails = await recipients_for_roles(
        {rbac.LEAD_PHARMACIST, rbac.PHARMACIST_ADMIN, rbac.SYSTEM_OWNER}
    )
    extra = f"\nProduct: <b>{product_name}</b>" if product_name else ""
    body = (
        f"💬 <b>New pharmacist question</b>{extra}\n"
        f"From: {cust_name or 'customer'} (id <code>{cust_id}</code>)\n\n{text}"
    )
    for tid in telegram_ids:
        try:
            await bot.send_message(tid, body)
        except Exception:  # noqa: BLE001
            continue

    plain = body.replace("<b>", "").replace("</b>", "")
    from app.core.config import get_settings

    await send_email(emails, f"[{get_settings().pharmacy_name}] New pharmacist question", plain)
