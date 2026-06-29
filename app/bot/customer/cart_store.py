"""Cart persistence inside the aiogram FSM context (per-user, in-memory)."""
from __future__ import annotations

from decimal import Decimal

from aiogram.fsm.context import FSMContext


async def get_cart(state: FSMContext) -> list[dict]:
    data = await state.get_data()
    return data.get("cart", [])


async def save_cart(state: FSMContext, cart: list[dict]) -> None:
    await state.update_data(cart=cart)


async def add_item(state: FSMContext, *, product_id: str, name: str, unit_price: str, requires_prescription: bool) -> None:
    cart = await get_cart(state)
    for item in cart:
        if item["product_id"] == product_id:
            item["qty"] += 1
            break
    else:
        cart.append(
            {
                "product_id": product_id,
                "name": name,
                "unit_price": unit_price,  # str of Decimal, JSON-safe
                "qty": 1,
                "requires_prescription": requires_prescription,
            }
        )
    await save_cart(state, cart)


async def set_qty(state: FSMContext, product_id: str, qty: int) -> None:
    cart = await get_cart(state)
    cart = [i for i in cart if not (i["product_id"] == product_id and qty <= 0)]
    for item in cart:
        if item["product_id"] == product_id:
            item["qty"] = qty
    await save_cart(state, cart)


async def remove_item(state: FSMContext, product_id: str) -> None:
    cart = [i for i in await get_cart(state) if i["product_id"] != product_id]
    await save_cart(state, cart)


async def clear_cart(state: FSMContext) -> None:
    await state.update_data(cart=[])


def cart_subtotal(cart: list[dict]) -> Decimal:
    return sum((Decimal(i["unit_price"]) * i["qty"] for i in cart), Decimal("0"))


def cart_has_prescription(cart: list[dict]) -> bool:
    return any(i.get("requires_prescription") for i in cart)
