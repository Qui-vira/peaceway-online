"""Checkout: collect delivery details, show profit-protected totals, create order."""
from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.customer import cart_store
from app.bot.customer.states import CheckoutFlow
from app.bot.keyboards.customer import back_to_menu
from app.core.db import get_session
from app.models import DeliveryZone, FeeSetting, PaymentMethod
from app.services.orders import create_order
from app.services.pricing import FeeConfig, QuoteItem, quote_order

router = Router(name="customer-checkout")


@router.callback_query(F.data == "checkout:start")
async def start(call: CallbackQuery, state: FSMContext) -> None:
    cart = await cart_store.get_cart(state)
    if not cart:
        await call.answer("Your cart is empty.", show_alert=True)
        return
    await state.set_state(CheckoutFlow.full_name)
    await call.message.edit_text(
        "📝 <b>Delivery details</b>\n\nWhat is the full name of the person receiving the order?",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.message(CheckoutFlow.full_name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text.strip())
    await state.set_state(CheckoutFlow.phone)
    await message.answer("📞 Phone number for delivery?")


@router.message(CheckoutFlow.phone, F.text)
async def got_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.text.strip())
    await state.set_state(CheckoutFlow.address)
    await message.answer("🏠 Delivery address (street, house number)?")


@router.message(CheckoutFlow.address, F.text)
async def got_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    async with get_session() as session:
        zones = (
            await session.execute(
                select(DeliveryZone).where(DeliveryZone.is_active.is_(True)).order_by(DeliveryZone.fee)
            )
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    for z in zones:
        kb.button(text=f"{z.name} · ₦{z.fee:,.0f}", callback_data=f"zone:{z.name}")
    kb.adjust(1)
    await state.set_state(CheckoutFlow.area)
    await message.answer("📍 Choose your delivery area:", reply_markup=kb.as_markup())


@router.callback_query(CheckoutFlow.area, F.data.startswith("zone:"))
async def got_area(call: CallbackQuery, state: FSMContext) -> None:
    area = call.data.split("zone:", 1)[1]
    await state.update_data(area=area)
    await state.set_state(CheckoutFlow.landmark)
    await call.message.edit_text("🏁 Any landmark to help the rider find you?")
    await call.answer()


@router.message(CheckoutFlow.landmark, F.text)
async def got_landmark(message: Message, state: FSMContext) -> None:
    await state.update_data(landmark=message.text.strip())
    await state.set_state(CheckoutFlow.preferred_time)
    await message.answer("🕒 Preferred delivery time? (e.g. <i>Today before 5pm</i>, or type <i>Any</i>)")


@router.message(CheckoutFlow.preferred_time, F.text)
async def got_time(message: Message, state: FSMContext) -> None:
    await state.update_data(preferred_time=message.text.strip())
    await state.set_state(CheckoutFlow.note)
    await message.answer("🗒 Any extra note for your order? (or type <i>None</i>)")


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
    kb.button(text="❌ Cancel", callback_data="menu:home")
    kb.adjust(1)
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

    from app.models import Customer

    async with get_session() as session:
        customer = (
            await session.execute(select(Customer).where(Customer.telegram_id == call.from_user.id))
        ).scalar_one_or_none()
        if customer is None:
            customer = Customer(telegram_id=call.from_user.id, full_name=data.get("full_name"))
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

    await cart_store.clear_cart(state)
    await state.clear()

    if has_rx:
        await call.message.edit_text(
            f"🧾 Order <b>{order_code}</b> received.\n\n💊 Your order contains a medicine that "
            "requires pharmacist review before payment. Our pharmacist will review it shortly.",
            reply_markup=back_to_menu(),
        )
    else:
        from app.bot.customer.payment import show_payment_methods

        await show_payment_methods(call, order_code, quote.total)
    await call.answer()
