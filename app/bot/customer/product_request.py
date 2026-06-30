"""Custom product/supplement request flow ("Request This Product" /
"I couldn't find my medicine"). Treated as a customer lead: collects contact
details and urgency so Peaceway can follow up, not just a one-shot ticket."""
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
from app.services.customers import get_or_create_customer, is_valid_email, save_email
from app.services.rbac_service import recipients_for_roles

router = Router(name="customer-product-request")
log = get_logger("product_request")

_URGENCY_LABELS = {
    "TODAY": "🔥 Today",
    "WITHIN_24H": "⏰ Within 24 hours",
    "THIS_WEEK": "🗓 This week",
    "JUST_CHECKING": "🤔 Just checking",
}


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
    await state.update_data(req_area=area)

    async with get_session() as session:
        customer = await get_or_create_customer(session, call.from_user.id, call.from_user.full_name)
        saved_phone = customer.phone

    if saved_phone:
        await state.update_data(req_phone=saved_phone)
        await _ask_email_step(call.message, state)
    else:
        await state.set_state(ProductRequestFlow.phone)
        await call.message.edit_text(
            "📞 Your phone number for this request?", reply_markup=back_cancel("menu:order")
        )
    await call.answer()


@router.message(ProductRequestFlow.phone, F.text)
async def got_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(req_phone=message.text.strip())
    await _ask_email_step(message, state)


async def _ask_email_step(target, state: FSMContext) -> None:
    telegram_id = target.chat.id if hasattr(target, "chat") else target.from_user.id
    async with get_session() as session:
        customer = await get_or_create_customer(session, telegram_id, None)
        existing_email = customer.email

    if existing_email:
        await state.update_data(req_email=existing_email)
        await _ask_urgency(target, state)
        return

    await state.set_state(ProductRequestFlow.email)
    text = "📧 Your email? (so we can notify you when it's available) — or type <i>skip</i>"
    if hasattr(target, "edit_text"):
        await target.edit_text(text, reply_markup=back_cancel("menu:order"))
    else:
        await target.answer(text, reply_markup=back_cancel("menu:order"))


@router.message(ProductRequestFlow.email, F.text)
async def got_email(message: Message, state: FSMContext) -> None:
    val = message.text.strip()
    if val.lower() != "skip":
        if not is_valid_email(val):
            await message.answer(
                "That email does not look correct. Please enter a valid email like "
                "name@example.com, or type skip."
            )
            return
        await state.update_data(req_email=val)
        async with get_session() as session:
            customer = await get_or_create_customer(session, message.from_user.id, message.from_user.full_name)
            await save_email(session, customer, val, "product_request", message.from_user.id)
    await _ask_urgency(message, state)


def _urgency_kb():
    kb = InlineKeyboardBuilder()
    for key, label in _URGENCY_LABELS.items():
        kb.button(text=label, callback_data=f"prequrg:{key}")
    kb.adjust(2)
    return kb.as_markup()


async def _ask_urgency(target, state: FSMContext) -> None:
    await state.set_state(ProductRequestFlow.urgency)
    text = "⏱ How urgently do you need this?"
    if hasattr(target, "edit_text"):
        await target.edit_text(text, reply_markup=_urgency_kb())
    else:
        await target.answer(text, reply_markup=_urgency_kb())


@router.callback_query(ProductRequestFlow.urgency, F.data.startswith("prequrg:"))
async def got_urgency(call: CallbackQuery, state: FSMContext) -> None:
    urgency = call.data.split("prequrg:", 1)[1]
    await state.update_data(req_urgency=urgency)
    await state.set_state(ProductRequestFlow.note)
    await call.message.edit_text("🗒 Any extra note? — or type <i>skip</i>", reply_markup=back_cancel("menu:order"))
    await call.answer()


@router.message(ProductRequestFlow.note, F.text)
async def got_note(message: Message, state: FSMContext) -> None:
    val = message.text.strip()
    await state.update_data(req_note=None if val.lower() == "skip" else val)
    data = await state.get_data()
    await state.clear()

    async with get_session() as session:
        customer = await get_or_create_customer(session, message.from_user.id, message.from_user.full_name)
        req = ProductRequest(
            customer_id=customer.id,
            product_name=data.get("req_name", "(unspecified)"),
            strength=data.get("req_strength"),
            form=data.get("req_form"),
            quantity=data.get("req_quantity"),
            note=data.get("req_note"),
            delivery_area=data.get("req_area"),
            customer_phone=data.get("req_phone"),
            customer_email=data.get("req_email") or customer.email,
            urgency=data.get("req_urgency"),
        )
        session.add(req)
        await session.flush()
        from app.services.product_requests import add_message

        await add_message(
            session, req, "customer",
            data.get("req_note") or f"Requested {req.product_name} ({req.quantity or '?'} units)",
        )
        cust_name = customer.full_name
        req_id = req.id
        snapshot = (
            req.product_name, req.strength, req.form, req.quantity, req.delivery_area,
            req.customer_phone, req.urgency, req.is_medicine,
        )

    try:
        await _alert(message.bot, cust_name, message.from_user.id, *snapshot)
    except Exception as exc:  # noqa: BLE001
        log.error("product_request_alert_failed", error=str(exc))

    kb = InlineKeyboardBuilder()
    if not data.get("req_email"):
        kb.button(text="✉️ Add Email", callback_data="preq:addemail")
    kb.button(text="📋 Track My Request", callback_data="menu:track_requests")
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await message.answer(
        "✅ Thank you. Peaceway has received your request. We will check availability and update you "
        "here. You can also add your email so we can notify you when it becomes available.",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data == "preq:addemail")
async def add_email_cta(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.profile import ask_update_email

    await ask_update_email(call, state)


async def _alert(bot, cust_name, cust_tid, name, strength, form, qty, area, phone, urgency, is_medicine) -> None:
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
        + f"Area: {area}\n"
        + (f"Phone: {phone}\n" if phone else "")
        + (f"Urgency: {_URGENCY_LABELS.get(urgency, urgency)}\n" if urgency else "")
    )
    for tid in telegram_ids:
        try:
            await bot.send_message(tid, text)
        except Exception:  # noqa: BLE001
            continue
