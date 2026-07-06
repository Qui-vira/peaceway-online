"""Cart view and quantity management."""
from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.customer import cart_store
from app.bot.keyboards.customer import back_to_menu

router = Router(name="customer-cart")


def _cart_text(cart: list[dict]) -> str:
    if not cart:
        return "🧺 Your cart is empty."
    lines = ["🧺 <b>Your Cart</b>\n"]
    for i in cart:
        line_total = Decimal(i["unit_price"]) * i["qty"]
        lines.append(f"• {i['name']}\n   {i['qty']} × ₦{Decimal(i['unit_price']):,.0f} = ₦{line_total:,.0f}")
    lines.append(f"\n<b>Subtotal: ₦{cart_store.cart_subtotal(cart):,.0f}</b>")
    lines.append("<i>Delivery & fees are added at checkout.</i>")
    return "\n".join(lines)


def _cart_kb(cart: list[dict]):
    kb = InlineKeyboardBuilder()
    for i in cart:
        pid = i["product_id"]
        kb.button(text=f"➖ {i['name'][:18]}", callback_data=f"cqty:{pid}:dec")
        kb.button(text=f"{i['qty']}", callback_data="noop")
        kb.button(text="➕", callback_data=f"cqty:{pid}:inc")
        kb.button(text="🗑", callback_data=f"crm:{pid}")
    if cart:
        kb.button(text="✅ Checkout", callback_data="checkout:start")
        kb.button(text="🗑 Clear cart", callback_data="cart:clear")
    kb.button(text="➕ Add more", callback_data="menu:order")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    # 4 controls per cart row, then 1-per-row action buttons.
    sizes = [4] * len(cart) + [1] * (4 if cart else 2)
    kb.adjust(*sizes)
    return kb.as_markup()


async def show_cart(call: CallbackQuery, state: FSMContext) -> None:
    cart = await cart_store.get_cart(state)
    await call.message.edit_text(_cart_text(cart), reply_markup=_cart_kb(cart))


@router.callback_query(F.data == "cart:view")
async def view_cart(call: CallbackQuery, state: FSMContext) -> None:
    await show_cart(call, state)
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery) -> None:
    await call.answer()


@router.callback_query(F.data.startswith("cqty:"))
async def change_qty(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer()
        return
    _, pid, op = parts
    cart = await cart_store.get_cart(state)
    current = next((i["qty"] for i in cart if i["product_id"] == pid), 0)
    new_qty = current + 1 if op == "inc" else current - 1
    await cart_store.set_qty(state, pid, new_qty)
    await show_cart(call, state)
    await call.answer()


@router.callback_query(F.data.startswith("crm:"))
async def remove(call: CallbackQuery, state: FSMContext) -> None:
    pid = call.data.split("crm:", 1)[1]
    await cart_store.remove_item(state, pid)
    await show_cart(call, state)
    await call.answer("Removed")


@router.callback_query(F.data == "cart:clear")
async def clear(call: CallbackQuery, state: FSMContext) -> None:
    await cart_store.clear_cart(state)
    await call.message.edit_text("🧺 Cart cleared.", reply_markup=back_to_menu())
    await call.answer()
