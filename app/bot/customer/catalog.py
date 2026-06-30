"""Browse, search, and product-card handlers."""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.customer import cart_store
from app.bot.customer.states import SearchFlow
from app.bot.keyboards.customer import back_cancel, back_to_menu
from app.core.db import get_session
from app.models import Product
from app.services import catalog

router = Router(name="customer-catalog")


_is_buyable = catalog.is_buyable  # shared single source of truth


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


def _results_kb(products: list[Product], back_cb: str = "menu:order"):
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=_product_line(p)[:60], callback_data=f"prod:{p.id}")
    kb.button(text="⬅️ Back", callback_data=back_cb)
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def _not_found_kb():
    """Action row for 'no results' / unpriced products — never a dead end."""
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Ask Pharmacist", callback_data="menu:ask")
    kb.button(text="📝 Request This Product", callback_data="preq:start")
    kb.button(text="🔎 Search Again", callback_data="order:search")
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


# ── Order entry: search or browse ────────────────────────────────────────────
async def _render_order_menu(call: CallbackQuery) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Search by name", callback_data="order:search")
    kb.button(text="🗂 Browse categories", callback_data="order:browse")
    kb.button(text="🧺 View cart", callback_data="cart:view")
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(
        "🛒 <b>Order Medicine</b>\n\nSearch for a product or browse our categories.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "menu:order")
async def order_menu(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(call, state, source="order", resume=lambda: _render_order_menu(call)):
        return
    await _render_order_menu(call)


@router.callback_query(F.data == "order:search")
async def ask_search(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchFlow.waiting_query)
    await call.message.edit_text(
        "🔎 Type the medicine name you're looking for (e.g. <i>Paracetamol</i>).",
        reply_markup=back_cancel("menu:order"),
    )
    await call.answer()


async def render_search_results(answerable, state: FSMContext, query: str) -> None:
    """Search and reply with results. `answerable` just needs `.answer(text, reply_markup=...)`
    (a Message works directly; callers can pass `call.message` too)."""
    async with get_session() as session:
        results = await catalog.search_products(session, query)
    if not results:
        await answerable.answer(
            f"😕 No products found for “{query}”.\n\nWhat would you like to do?",
            reply_markup=_not_found_kb(),
        )
        return
    await state.update_data(last_list_kind="search", last_query=query)
    await answerable.answer(f"Results for “{query}”:", reply_markup=_results_kb(results))


@router.message(SearchFlow.waiting_query, F.text)
async def do_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await render_search_results(message, state, message.text)


@router.callback_query(F.data == "order:browse")
async def browse_categories(call: CallbackQuery) -> None:
    async with get_session() as session:
        cats = await catalog.categories(session)
    kb = InlineKeyboardBuilder()
    for c in cats:
        kb.button(text=c, callback_data=f"cat:{c}")
    kb.button(text="⬅️ Back", callback_data="menu:order")
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text("🗂 <b>Categories</b>", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def category_products(call: CallbackQuery, state: FSMContext) -> None:
    name = call.data.split("cat:", 1)[1]
    async with get_session() as session:
        products = await catalog.products_in_category(session, name)
    if not products:
        await call.message.edit_text(
            "No products in this category yet.", reply_markup=back_cancel("order:browse")
        )
        await call.answer()
        return
    await state.update_data(last_list_kind="category", last_category=name)
    await call.message.edit_text(f"🗂 <b>{name}</b>", reply_markup=_results_kb(products, "order:browse"))
    await call.answer()


@router.callback_query(F.data == "menu:popular")
async def popular(call: CallbackQuery, state: FSMContext) -> None:
    async with get_session() as session:
        products = await catalog.popular_products(session)
    if not products:
        await call.message.edit_text(
            "⭐ Our popular products list is being set up. Use search or browse for now.",
            reply_markup=back_to_menu(),
        )
        await call.answer()
        return
    await state.update_data(last_list_kind="popular")
    await call.message.edit_text(
        "⭐ <b>Popular Products</b>", reply_markup=_results_kb(products, "menu:home")
    )
    await call.answer()


@router.callback_query(F.data == "catalog:back")
async def back_to_last_list(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    kind = data.get("last_list_kind")
    async with get_session() as session:
        if kind == "search" and data.get("last_query"):
            results = await catalog.search_products(session, data["last_query"])
            await call.message.edit_text(
                f"Results for “{data['last_query']}”:", reply_markup=_results_kb(results)
            )
        elif kind == "category" and data.get("last_category"):
            results = await catalog.products_in_category(session, data["last_category"])
            await call.message.edit_text(
                f"🗂 <b>{data['last_category']}</b>", reply_markup=_results_kb(results, "order:browse")
            )
        elif kind == "popular":
            results = await catalog.popular_products(session)
            await call.message.edit_text(
                "⭐ <b>Popular Products</b>", reply_markup=_results_kb(results, "menu:home")
            )
        else:
            await call.message.edit_text(
                "🛒 <b>Order Medicine</b>\n\nSearch for a product or browse our categories.",
                reply_markup=back_to_menu(),
            )
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
            kb.button(text="🧺 View Cart", callback_data="cart:view")
        elif p.requires_prescription or p.requires_review:
            text = (
                f"{title}\n{body}\n\n💊 <b>This medicine requires pharmacist review or a valid "
                "prescription before it can be supplied.</b>"
            )
            kb.button(text="📄 Upload Prescription", callback_data=f"rx:{p.id}")
            kb.button(text="💬 Ask Pharmacist", callback_data=f"askp:{p.id}")
            kb.button(text="📝 Request This Product", callback_data="preq:start")
        else:
            text = f"{title}\n{body}\n\nℹ️ <b>Ask pharmacist for price & availability.</b>"
            kb.button(text="💬 Ask Pharmacist", callback_data=f"askp:{p.id}")
            kb.button(text="📝 Request This Product", callback_data="preq:start")
        kb.button(text="🔎 Search Again", callback_data="order:search")
        kb.button(text="⬅️ Back to results", callback_data="catalog:back")
        kb.button(text="🏠 Main Menu", callback_data="menu:home")
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
