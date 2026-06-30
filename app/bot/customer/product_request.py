"""Custom product/supplement request flow ("Request This Product" /
"I couldn't find my medicine")."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.customer.states import ProductRequestFlow
from app.bot.keyboards.customer import back_cancel, back_to_menu
from app.core import rbac
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import DeliveryZone, ProductRequest
from app.services.customers import get_or_create_customer
from app.services.rbac_service import recipients_for_roles

router = Router(name="customer-product-request")
log = get_logger("product_request")


async def _render_start(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    prefill = data.get("last_query")
    await state.set_state(ProductRequestFlow.product_name)
    if prefill:
        await state.update_data(req_name=prefill)
        kb = InlineKeyboardBuilder()
        kb.button(text=f"✅ Use “{prefill}”", callback_data="preq:useprefill")
        kb.button(text="✏️ Type a different name", callback_data="preq:retype")
        kb.button(text="❌ Cancel", callback_data="menu:home")
        kb.adjust(1)
        await call.message.edit_text(
            f"📝 <b>Request This Product</b>\n\nUse “{prefill}” as the product name?",
            reply_markup=kb.as_markup(),
        )
    else:
        await call.message.edit_text(
            "📝 <b>Request This Product</b>\n\nWhat medicine or supplement are you looking for?",
            reply_markup=back_cancel("menu:order"),
        )
    await call.answer()


@router.callback_query(F.data == "preq:start")
async def start(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(call, state, source="product_request", resume=lambda: _render_start(call, state)):
        return
    await _render_start(call, state)


@router.callback_query(ProductRequestFlow.product_name, F.data == "preq:useprefill")
async def use_prefill(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProductRequestFlow.strength)
    await call.message.edit_text(
        "💊 Strength? (e.g. 500mg) — or type <i>skip</i>", reply_markup=back_cancel("menu:order")
    )
    await call.answer()


@router.callback_query(ProductRequestFlow.product_name, F.data == "preq:retype")
async def retype(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "📝 What medicine or supplement are you looking for?", reply_markup=back_cancel("menu:order")
    )
    await call.answer()


@router.message(ProductRequestFlow.product_name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(req_name=message.text.strip())
    await state.set_state(ProductRequestFlow.strength)
    await message.answer(
        "💊 Strength? (e.g. 500mg) — or type <i>skip</i>", reply_markup=back_cancel("menu:order")
    )


@router.message(ProductRequestFlow.strength, F.text)
async def got_strength(message: Message, state: FSMContext) -> None:
    val = message.text.strip()
    await state.update_data(req_strength=None if val.lower() == "skip" else val)
    await state.set_state(ProductRequestFlow.form)
    await message.answer(
        "💊 Form? (tablet, syrup, injection...) — or type <i>skip</i>", reply_markup=back_cancel("menu:order")
    )


@router.message(ProductRequestFlow.form, F.text)
async def got_form(message: Message, state: FSMContext) -> None:
    val = message.text.strip()
    await state.update_data(req_form=None if val.lower() == "skip" else val)
    await state.set_state(ProductRequestFlow.quantity)
    await message.answer("🔢 How many do you need?", reply_markup=back_cancel("menu:order"))


@router.message(ProductRequestFlow.quantity, F.text)
async def got_quantity(message: Message, state: FSMContext) -> None:
    await state.update_data(req_quantity=message.text.strip())
    await state.set_state(ProductRequestFlow.note)
    await message.answer("🗒 Any extra note? — or type <i>skip</i>", reply_markup=back_cancel("menu:order"))


@router.message(ProductRequestFlow.note, F.text)
async def got_note(message: Message, state: FSMContext) -> None:
    val = message.text.strip()
    await state.update_data(req_note=None if val.lower() == "skip" else val)
    async with get_session() as session:
        zones = (
            await session.execute(
                select(DeliveryZone).where(DeliveryZone.is_active.is_(True)).order_by(DeliveryZone.fee)
            )
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    for z in zones:
        kb.button(text=z.name, callback_data=f"preqzone:{z.name}")
    kb.button(text="❌ Cancel", callback_data="menu:home")
    kb.adjust(2)
    await state.set_state(ProductRequestFlow.area)
    await message.answer("📍 Your delivery area?", reply_markup=kb.as_markup())


@router.callback_query(ProductRequestFlow.area, F.data.startswith("preqzone:"))
async def got_area(call: CallbackQuery, state: FSMContext) -> None:
    area = call.data.split("preqzone:", 1)[1]
    data = await state.get_data()
    await state.clear()

    async with get_session() as session:
        customer = await get_or_create_customer(session, call.from_user.id, call.from_user.full_name)
        req = ProductRequest(
            customer_id=customer.id,
            product_name=data.get("req_name", "(unspecified)"),
            strength=data.get("req_strength"),
            form=data.get("req_form"),
            quantity=data.get("req_quantity"),
            note=data.get("req_note"),
            delivery_area=area,
        )
        session.add(req)
        await session.flush()
        cust_name = customer.full_name
        req_name, req_strength, req_form, req_qty, req_area, req_is_med = (
            req.product_name, req.strength, req.form, req.quantity, req.delivery_area, req.is_medicine,
        )

    try:
        await _alert(call.bot, cust_name, call.from_user.id, req_name, req_strength, req_form, req_qty, req_area, req_is_med)
    except Exception as exc:  # noqa: BLE001
        log.error("product_request_alert_failed", error=str(exc))

    await call.message.edit_text(
        "✅ Thank you! We've received your request and our team will get back to you about availability.",
        reply_markup=back_to_menu(),
    )
    await call.answer()


async def _alert(bot, cust_name, cust_tid, name, strength, form, qty, area, is_medicine) -> None:
    roles = {rbac.SALES_SUPPORT, rbac.SYSTEM_OWNER}
    if is_medicine:
        roles |= {rbac.LEAD_PHARMACIST, rbac.PHARMACIST_ADMIN}
    telegram_ids, _emails = await recipients_for_roles(roles)
    text = (
        f"📝 <b>New product request</b>\n"
        f"From: {cust_name or 'customer'} (id <code>{cust_tid}</code>)\n"
        f"Product: {name}\n"
        + (f"Strength: {strength}\n" if strength else "")
        + (f"Form: {form}\n" if form else "")
        + (f"Qty: {qty}\n" if qty else "")
        + f"Area: {area}"
    )
    for tid in telegram_ids:
        try:
            await bot.send_message(tid, text)
        except Exception:  # noqa: BLE001
            continue
