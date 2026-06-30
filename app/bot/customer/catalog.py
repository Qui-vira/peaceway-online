"""Browse, search, and product-card handlers."""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.customer import cart_store
from app.bot.customer.states import SearchFlow
from app.bot.keyboards.customer import back_to_menu
from app.core.db import get_session
from app.models import Product
from app.services import catalog

router = Router(name="customer-catalog")


def _is_buyable(p: Product) -> bool:
    return bool(
        p.is_listed
        and not p.requires_prescription
        and not p.requires_review
        and p.pricing
        and p.pricing.is_in_stock
        and p.pricing.selling_price
        and p.pricing.selling_price > 0
    )


def _product_line(p: Product) -> str:
    bits = [p.name]
    if p.strength:
        bits.append(p.strength)
    label = " ".join(bits)
    if _is_buyable(p):
        return f"{label} · ₦{p.pricing.selling_price:,.0f}"
    if p.requires_prescription:
        return f"{label} · 💊 Rx"
    return f"{label} · ask pharmacist"


def _results_kb(products: list[Product]):
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=_product_line(p)[:60], callback_data=f"prod:{p.id}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


# ── Order entry: search or browse ────────────────────────────────────────────
@router.callback_query(F.data == "menu:order")
async def order_menu(call: CallbackQuery) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Search by name", callback_data="order:search")
    kb.button(text="🗂 Browse categories", callback_data="order:browse")
    kb.button(text="🧺 View cart", callback_data="cart:view")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(
        "🛒 <b>Order Medicine</b>\n\nSearch for a product or browse our categories.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "order:search")
async def ask_search(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchFlow.waiting_query)
    await call.message.edit_text(
        "🔎 Type the medicine name you're looking for (e.g. <i>Paracetamol</i>).",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.message(SearchFlow.waiting_query, F.text)
async def do_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with get_session() as session:
        results = await catalog.search_products(session, message.text)
    if not results:
        await message.answer(
            f"No products found for “{message.text}”. Try another name or browse categories.",
            reply_markup=back_to_menu(),
        )
        return
    await message.answer(
        f"Results for “{message.text}”:", reply_markup=_results_kb(results)
    )


@router.callback_query(F.data == "order:browse")
async def browse_categories(call: CallbackQuery) -> None:
    async with get_session() as session:
        cats = await catalog.categories(session)
    kb = InlineKeyboardBuilder()
    for c in cats:
        kb.button(text=c, callback_data=f"cat:{c}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text("🗂 <b>Categories</b>", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def category_products(call: CallbackQuery) -> None:
    name = call.data.split("cat:", 1)[1]
    async with get_session() as session:
        products = await catalog.products_in_category(session, name)
    if not products:
        await call.message.edit_text("No products in this category yet.", reply_markup=back_to_menu())
        await call.answer()
        return
    await call.message.edit_text(f"🗂 <b>{name}</b>", reply_markup=_results_kb(products))
    await call.answer()


@router.callback_query(F.data == "menu:popular")
async def popular(call: CallbackQuery) -> None:
    async with get_session() as session:
        products = await catalog.popular_products(session)
    if not products:
        await call.message.edit_text(
            "⭐ Our popular products list is being set up. Use search or browse for now.",
            reply_markup=back_to_menu(),
        )
        await call.answer()
        return
    await call.message.edit_text("⭐ <b>Popular Products</b>", reply_markup=_results_kb(products))
    await call.answer()


# ── Product card ─────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("prod:"))
async def product_card(call: CallbackQuery) -> None:
    product_id = UUID(call.data.split("prod:", 1)[1])
    async with get_session() as session:
        p = await catalog.get_product(session, product_id)
        if p is None:
            await call.answer("Product not found.", show_alert=True)
            return
        buyable = _is_buyable(p)
        title = f"<b>{p.name}</b>"
        details = []
        if p.generic_name and p.generic_name.lower() != p.name.lower():
            details.append(f"Generic: {p.generic_name}")
        if p.strength:
            details.append(f"Strength: {p.strength}")
        if p.dosage_form:
            details.append(f"Form: {p.dosage_form}")
        if p.manufacturer:
            details.append(f"Maker: {p.manufacturer}")
        body = "\n".join(details)

        kb = InlineKeyboardBuilder()
        if buyable:
            price = f"₦{p.pricing.selling_price:,.0f}"
            text = f"{title}\n{body}\n\n💵 <b>{price}</b>\n✅ In stock"
            kb.button(text=f"➕ Add to Cart ({price})", callback_data=f"add:{p.id}")
        elif p.requires_prescription or p.requires_review:
            text = (
                f"{title}\n{body}\n\n💊 <b>This medicine requires pharmacist review or a valid "
                "prescription before it can be supplied.</b>"
            )
            kb.button(text="📄 Upload Prescription", callback_data=f"rx:{p.id}")
            kb.button(text="💬 Ask Pharmacist", callback_data="menu:ask")
        else:
            text = (
                f"{title}\n{body}\n\nℹ️ <b>Ask pharmacist for price & availability.</b>"
            )
            kb.button(text="💬 Ask Pharmacist", callback_data="menu:ask")
        kb.button(text="🧺 View Cart", callback_data="cart:view")
        kb.button(text="⬅️ Main Menu", callback_data="menu:home")
        kb.adjust(1)
        await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


# ── Add to cart ──────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("add:"))
async def add_to_cart(call: CallbackQuery, state: FSMContext) -> None:
    product_id = UUID(call.data.split("add:", 1)[1])
    async with get_session() as session:
        p = await catalog.get_product(session, product_id)
        if p is None or not _is_buyable(p):
            await call.answer("This item is not available to order.", show_alert=True)
            return
        await cart_store.add_item(
            state,
            product_id=str(p.id),
            name=p.name,
            unit_price=str(p.pricing.selling_price),
            requires_prescription=p.requires_prescription,
        )
    await call.answer("Added to cart ✅")
    from app.bot.customer.cart import show_cart

    await show_cart(call, state)
