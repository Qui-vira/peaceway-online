"""Checkout: collect delivery details, show profit-protected totals, create order.

Every step has a Back button (to the previous step, preserving already-entered
data) and a Cancel button (to Main Menu, clearing the flow).
"""
from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.customer import cart_store
from app.bot.customer.states import CheckoutFlow
from app.bot.keyboards.customer import back_cancel
from app.core.db import get_session
from app.models import DeliveryZone, FeeSetting, PaymentMethod
from app.services.orders import create_order
from app.services.pricing import FeeConfig, QuoteItem, quote_order

router = Router(name="customer-checkout")

_STEP_TEXT = {
    "name": "📝 <b>Delivery details</b>\n\nWhat is the full name of the person receiving the order?",
    "phone": "📞 Phone number for delivery?",
    "address": "🏠 Delivery address (street, house number)?",
    "landmark": "🏁 Any landmark to help the rider find you?",
    "time": "🕒 Preferred delivery time? (e.g. <i>Today before 5pm</i>, or type <i>Any</i>)",
    "note": "🗒 Any extra note for your order? (or type <i>None</i>)",
}
# Each step's Back button returns to the previous step's callback (or a real screen).
_STEP_BACK = {
    "name": "cart:view",
    "phone": "checkout:back:name",
    "address": "checkout:back:phone",
    "landmark": "checkout:back:area",
    "time": "checkout:back:landmark",
    "note": "checkout:back:time",
}
_STEP_STATE = {
    "name": CheckoutFlow.full_name,
    "phone": CheckoutFlow.phone,
    "address": CheckoutFlow.address,
    "landmark": CheckoutFlow.landmark,
    "time": CheckoutFlow.preferred_time,
    "note": CheckoutFlow.note,
}


async def _zones_kb():
    async with get_session() as session:
        zones = (
            await session.execute(
                select(DeliveryZone).where(DeliveryZone.is_active.is_(True)).order_by(DeliveryZone.fee)
            )
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    for z in zones:
        kb.button(text=f"{z.name} · ₦{z.fee:,.0f}", callback_data=f"zone:{z.name}")
    kb.button(text="⬅️ Back", callback_data="checkout:back:address")
    kb.button(text="❌ Cancel", callback_data="menu:home")
    kb.adjust(2)
    return kb.as_markup()


@router.callback_query(F.data == "checkout:start")
async def start(call: CallbackQuery, state: FSMContext) -> None:
    cart = await cart_store.get_cart(state)
    if not cart:
        await call.answer("Your cart is empty.", show_alert=True)
        return
    await state.set_state(CheckoutFlow.full_name)
    await call.message.edit_text(_STEP_TEXT["name"], reply_markup=back_cancel("cart:view"))
    await call.answer()


@router.callback_query(F.data.startswith("checkout:back:"))
async def go_back(call: CallbackQuery, state: FSMContext) -> None:
    step = call.data.split("checkout:back:", 1)[1]
    if step == "area":
        await state.set_state(CheckoutFlow.area)
        await call.message.edit_text("📍 Choose your delivery area:", reply_markup=await _zones_kb())
        await call.answer()
        return
    await state.set_state(_STEP_STATE[step])
    await call.message.edit_text(_STEP_TEXT[step], reply_markup=back_cancel(_STEP_BACK[step]))
    await call.answer()


@router.message(CheckoutFlow.full_name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text.strip())
    await state.set_state(CheckoutFlow.phone)
    await message.answer(_STEP_TEXT["phone"], reply_markup=back_cancel(_STEP_BACK["phone"]))


@router.message(CheckoutFlow.phone, F.text)
async def got_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.text.strip())
    await state.set_state(CheckoutFlow.address)
    await message.answer(_STEP_TEXT["address"], reply_markup=back_cancel(_STEP_BACK["address"]))


@router.message(CheckoutFlow.address, F.text)
async def got_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    await state.set_state(CheckoutFlow.area)
    await message.answer("📍 Choose your delivery area:", reply_markup=await _zones_kb())


@router.callback_query(CheckoutFlow.area, F.data.startswith("zone:"))
async def got_area(call: CallbackQuery, state: FSMContext) -> None:
    area = call.data.split("zone:", 1)[1]
    await state.update_data(area=area)
    await state.set_state(CheckoutFlow.landmark)
    await call.message.edit_text(_STEP_TEXT["landmark"], reply_markup=back_cancel(_STEP_BACK["landmark"]))
    await call.answer()


@router.message(CheckoutFlow.landmark, F.text)
async def got_landmark(message: Message, state: FSMContext) -> None:
    await state.update_data(landmark=message.text.strip())
    await state.set_state(CheckoutFlow.preferred_time)
    await message.answer(_STEP_TEXT["time"], reply_markup=back_cancel(_STEP_BACK["time"]))


@router.message(CheckoutFlow.preferred_time, F.text)
async def got_time(message: Message, state: FSMContext) -> None:
    await state.update_data(preferred_time=message.text.strip())
    await state.set_state(CheckoutFlow.note)
    await message.answer(_STEP_TEXT["note"], reply_markup=back_cancel(_STEP_BACK["note"]))


async def _load_fee_and_zone(area: str) -> tuple[FeeConfig, Decimal]:
    async with get_session() as session:
        fee_row = await session.get(FeeSetting, 1)
        zone = (
            await session.execute(select(DeliveryZone).where(DeliveryZone.name == area))
        ).scalar_one_or_none()
    fees = FeeConfig(
        payment_fee_pct=fee_row.payment_fee_pct if fee_row else Decimal("0"),
        payment_fee_flat=fee_row.payment_fee_flat if fee_row else Decimal("0"),
        offramp_fee=fee_row.offramp_fee if fee_row else Decimal("0"),
        handling_fee=fee_row.handling_fee if fee_row else Decimal("0"),
    )
    delivery_fee = zone.fee if zone else Decimal("0")
    return fees, delivery_fee


def _summary_text(data: dict, quote) -> str:
    lines = ["🧾 <b>Confirm your order</b>", ""]
    for i in data["cart"]:
        lt = Decimal(i["unit_price"]) * i["qty"]
        lines.append(f"• {i['name']} ×{i['qty']} · ₦{lt:,.0f}")
    lines.append("")
    lines.append(f"Subtotal: ₦{quote.subtotal:,.0f}")
    lines.append(f"Delivery ({data['area']}): ₦{quote.delivery_fee:,.0f}")
    if quote.payment_fee:
        lines.append(f"Payment fee: ₦{quote.payment_fee:,.0f}")
    if quote.handling_fee:
        lines.append(f"Handling: ₦{quote.handling_fee:,.0f}")
    lines.append("")
    lines.append(f"<b>Total: ₦{quote.total:,.0f}</b>")
    lines.append("")
    lines.append(f"Deliver to: {data.get('full_name')}")
    lines.append(f"Phone: {data.get('phone')}")
    lines.append(f"Address: {data.get('address')}, {data.get('area')}")
    if data.get("landmark"):
        lines.append(f"Landmark: {data['landmark']}")
    return "\n".join(lines)


@router.message(CheckoutFlow.note, F.text)
async def got_note(message: Message, state: FSMContext) -> None:
    note = message.text.strip()
    await state.update_data(note=None if note.lower() == "none" else note)
    data = await state.get_data()
    cart = data.get("cart", [])
    fees, delivery_fee = await _load_fee_and_zone(data["area"])
    items = [QuoteItem(name=i["name"], quantity=i["qty"], selling_price=Decimal(i["unit_price"])) for i in cart]
    quote = quote_order(items, delivery_fee, fees, PaymentMethod.BANK_TRANSFER)
    await state.update_data(quote_total=str(quote.total))
    await state.set_state(CheckoutFlow.confirm)

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Confirm Order", callback_data="checkout:confirm")
    kb.button(text="⬅️ Back", callback_data="checkout:back:note")
    kb.button(text="❌ Cancel", callback_data="menu:home")
    kb.adjust(1, 2)
    await message.answer(_summary_text(data, quote), reply_markup=kb.as_markup())


@router.callback_query(CheckoutFlow.confirm, F.data == "checkout:confirm")
async def confirm(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await call.answer("Your cart is empty.", show_alert=True)
        return
    fees, delivery_fee = await _load_fee_and_zone(data["area"])
    items = [QuoteItem(name=i["name"], quantity=i["qty"], selling_price=Decimal(i["unit_price"])) for i in cart]
    quote = quote_order(items, delivery_fee, fees, PaymentMethod.BANK_TRANSFER)

    # Honour the total the customer saw on the summary screen. If a fee or zone
    # changed between summary and this tap, the recomputed total will differ -
    # re-show the summary rather than silently charging a new amount.
    locked_total = data.get("quote_total")
    if locked_total is not None and Decimal(locked_total) != quote.total:
        await state.update_data(quote_total=str(quote.total))
        await call.message.edit_text(
            _summary_text(data, quote)
            + "\n\n⚠️ Pricing was just updated - please review the new total and confirm again.",
            reply_markup=call.message.reply_markup,
        )
        await call.answer("Total updated - please confirm again.", show_alert=True)
        return

    from app.models import Customer

    async with get_session() as session:
        customer = (
            await session.execute(select(Customer).where(Customer.telegram_id == call.from_user.id))
        ).scalar_one_or_none()
        if customer is None:
            customer = Customer(
                telegram_id=call.from_user.id,
                full_name=data.get("full_name"),
                phone=data.get("phone"),
            )
            session.add(customer)
            await session.flush()
        order = await create_order(
            session,
            customer_id=customer.id,
            cart=cart,
            quote=quote,
            delivery=data,
            payment_method=None,
        )
        order_code = order.code
        has_rx = any(i.get("requires_prescription") for i in cart)
        sourcing_required = bool(order.sourcing and order.sourcing.sourcing_required)

    await cart_store.clear_cart(state)
    await state.clear()

    if has_rx:
        from app.bot.keyboards.customer import back_to_menu

        await call.message.edit_text(
            f"🧾 Order <b>{order_code}</b> received.\n\n💊 Your order contains a medicine that "
            "requires pharmacist review before payment. Our pharmacist will review it shortly.",
            reply_markup=back_to_menu(),
        )
    elif sourcing_required:
        from app.bot.keyboards.customer import back_to_menu
        from app.services.alerts import alert_sourcing_requested

        try:
            await alert_sourcing_requested(call.bot, order.id)
        except Exception:
            pass

        await call.message.edit_text(
            f"🧾 Order <b>{order_code}</b> received.\n\n"
            "One or more items are not currently in Peaceway stock, so we have moved the order into "
            "our approved sourcing workflow.\n\n"
            "We will confirm availability, price, expiry or batch standard, and pickup readiness before "
            "we show you a real ETA or request payment.",
            reply_markup=back_to_menu(),
        )
    else:
        from app.bot.customer.payment import show_payment_methods

        await show_payment_methods(call, order_code, quote.total)
    await call.answer()
