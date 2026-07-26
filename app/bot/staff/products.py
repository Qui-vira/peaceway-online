"""Admin Products management: search, view, edit price/stock/category/flags, history.

Gated on `edit_pricing` (System Owner via wildcard, Lead Pharmacist, Sales Support).
Every change is written to price_history + admin_activity_logs by
services.products_admin.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.staff.states import ProductAdminFlow
from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has
from app.models import AuditLog, PriceHistory, Product
from app.services import catalog, file_storage
from app.services.products_admin import VALID_CATEGORIES, apply_change

router = Router(name="staff-products")
log = get_logger(__name__)

_FIELD_LABELS = {
    "selling_price": "Update Selling Price",
    "cost_price": "Update Cost Price",
    "stock": "Update Stock",
}


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "edit_pricing"):
        await call.answer("Not authorised to manage products.", show_alert=True)
        return None
    return role_keys


@router.callback_query(F.data == "staff:products")
async def products_home(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Search Product", callback_data="padmin:search")
    kb.button(text="📷 Scan Product", callback_data="padmin:scan")
    if has(role_keys, "scan_inventory"):
        kb.button(text="🤖 Scan Stock From Photos", callback_data="invscan:start")
    kb.button(text="🧩 Backfill Product Data", callback_data="pbf:home")
    kb.button(text="📤 Import Products (CSV)", callback_data="padmin:csv")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text(
        "💊 <b>Products</b>\n\nSearch for a product to view and update its price, stock, "
        "category, and availability, or bulk-import prices from a CSV file.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


def _back_to_products_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data="staff:products")
    return kb.as_markup()


@router.callback_query(F.data == "padmin:search")
async def ask_search(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    await state.set_state(ProductAdminFlow.search)
    await call.message.edit_text("🔎 Type the product name to search.", reply_markup=_back_to_products_kb())
    await call.answer()


@router.message(ProductAdminFlow.search, F.text)
async def do_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with get_session() as session:
        results = await catalog.search_products(session, message.text, limit=12)
    if not results:
        await message.answer(f"No products found for “{message.text}”.", reply_markup=_back_to_products_kb())
        return
    kb = InlineKeyboardBuilder()
    for p in results:
        kb.button(text=p.name[:60], callback_data=f"padmin:view:{p.id}")
    kb.button(text="⬅️ Back", callback_data="staff:products")
    kb.adjust(1)
    await message.answer(f"Results for “{message.text}”:", reply_markup=kb.as_markup())


def _detail_text(p: Product) -> str:
    pr = p.pricing
    sell = f"₦{pr.selling_price:,.0f}" if pr and pr.selling_price else "not set"
    cost = f"₦{pr.cost_price:,.0f}" if pr and pr.cost_price else "not set"
    stock = pr.stock_qty if pr else 0
    avail = "✅ Available" if p.is_listed else "🚫 Hidden"
    rx = "💊 Prescription" if p.requires_prescription else "🟢 OTC"
    photo = "✅ set" if p.image_id else "— not set"
    return (
        f"💊 <b>{p.name}</b>\n"
        f"{p.strength or ''} {p.dosage_form or ''}\n\n"
        f"Category: {p.category or '-'}\n"
        f"Selling price: <b>{sell}</b>\n"
        f"Cost price: {cost}\n"
        f"Stock: {stock}\n"
        f"Status: {avail} · {rx}\n"
        f"Photo: {photo}"
    )


def _detail_kb(p: Product):
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Update Selling Price", callback_data=f"padmin:set:selling_price:{p.id}")
    kb.button(text="🏷 Update Cost Price", callback_data=f"padmin:set:cost_price:{p.id}")
    kb.button(text="📦 Update Stock", callback_data=f"padmin:set:stock:{p.id}")
    kb.button(text="🗂 Update Category", callback_data=f"padmin:cat:{p.id}")
    kb.button(
        text=("🚫 Mark Unavailable" if p.is_listed else "✅ Mark Available"),
        callback_data=f"padmin:avail:{p.id}",
    )
    kb.button(
        text=("🟢 Mark OTC" if p.requires_prescription else "💊 Mark Prescription"),
        callback_data=f"padmin:rx:{p.id}",
    )
    kb.button(
        text=("🖼 Replace Photo" if p.image_id else "📷 Add Photo"),
        callback_data=f"padmin:photo:{p.id}",
    )
    if p.image_id:
        kb.button(text="🗑 Remove Photo", callback_data=f"padmin:photodel:{p.id}")
    kb.button(text="🕘 View Price History", callback_data=f"padmin:hist:{p.id}")
    kb.button(text="🔎 Search Another", callback_data="padmin:search")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    return kb.as_markup()


async def _show_product(call: CallbackQuery, product_id: UUID) -> None:
    async with get_session() as session:
        p = await catalog.get_product(session, product_id)
        if p is None:
            await call.answer("Product not found.", show_alert=True)
            return
        text, kb = _detail_text(p), _detail_kb(p)
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("padmin:view:"))
async def view_product(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    await _show_product(call, UUID(call.data.split("padmin:view:", 1)[1]))
    await call.answer()


# ── Value-entry fields (selling/cost/stock) ──────────────────────────────────
@router.callback_query(F.data.startswith("padmin:set:"))
async def ask_value(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    _, _, field, pid = call.data.split(":", 3)
    await state.set_state(ProductAdminFlow.value)
    await state.update_data(field=field, product_id=pid)
    label = _FIELD_LABELS.get(field, field)
    await call.message.edit_text(f"✏️ <b>{label}</b>\n\nSend the new value (numbers only).")
    await call.answer()


@router.message(ProductAdminFlow.value, F.text)
async def got_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field, pid = data.get("field"), data.get("product_id")
    await state.clear()
    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p is None:
            await message.answer("Product not found.")
            return
        try:
            summary = await apply_change(session, p, field, message.text.strip(), message.from_user.id)
        except ValueError as exc:
            await message.answer(f"⚠️ {exc}\n\nPlease try again from the product menu.")
            return
        name = p.name
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Search another", callback_data="padmin:search")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await message.answer(f"✅ Updated <b>{name}</b>\n{summary}", reply_markup=kb.as_markup())


# ── Category picker ───────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("padmin:cat:"))
async def pick_category(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    pid = call.data.split("padmin:cat:", 1)[1]
    kb = InlineKeyboardBuilder()
    for c in VALID_CATEGORIES:
        kb.button(text=c, callback_data=f"padmin:setcat:{c}:{pid}")
    kb.button(text="⬅️ Back", callback_data=f"padmin:view:{pid}")
    kb.adjust(2)
    await call.message.edit_text("🗂 Choose a category:", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("padmin:setcat:"))
async def set_category(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    _, _, category, pid = call.data.split(":", 3)
    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p:
            await apply_change(session, p, "category", category, call.from_user.id)
    await _show_product(call, UUID(pid))
    await call.answer("Category updated ✅")


# ── Toggles ───────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("padmin:avail:"))
async def toggle_avail(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    pid = call.data.split("padmin:avail:", 1)[1]
    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p:
            await apply_change(session, p, "available", not p.is_listed, call.from_user.id)
    await _show_product(call, UUID(pid))
    await call.answer("Updated ✅")


@router.callback_query(F.data.startswith("padmin:rx:"))
async def toggle_rx(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    pid = call.data.split("padmin:rx:", 1)[1]
    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p:
            await apply_change(session, p, "rx", not p.requires_prescription, call.from_user.id)
    await _show_product(call, UUID(pid))
    await call.answer("Updated ✅")


# ── Product photo ─────────────────────────────────────────────────────────────
# Photos come from staff shooting the real stock, one product per photo. They do NOT
# come from the inventory scan pipeline: `InventoryScanItem.source_images` points at
# *shelf* photos containing many products at once, with no bounding boxes to crop by.
#
# This path does not go through products_admin.apply_change() — that function
# whitelists price/stock/category/availability/rx and raises on anything else. The
# image is set directly and audited here.
async def _log_photo_change(session, product: Product, action: str, admin_id: int) -> None:
    session.add(
        AuditLog(
            actor_telegram_id=admin_id,
            action=action,
            entity="product",
            entity_id=str(product.id),
            detail={"product_name": product.name},
        )
    )


@router.callback_query(F.data.startswith("padmin:photo:"))
async def ask_photo(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    pid = call.data.split("padmin:photo:", 1)[1]
    await state.set_state(ProductAdminFlow.photo_wait)
    await state.update_data(product_id=pid)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Cancel", callback_data=f"padmin:view:{pid}")
    await call.message.edit_text(
        "📷 <b>Send one photo of this product.</b>\n\n"
        "Shoot the actual pack on a plain surface, filling most of the frame. "
        "It is resized and shown on the website exactly as sent, so make sure the "
        "pack and strength match what customers receive.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.message(ProductAdminFlow.photo_wait, F.photo | F.document)
async def got_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    pid = data.get("product_id")

    if message.photo:
        file_id = message.photo[-1].file_id           # highest resolution offered
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        file_id = message.document.file_id
    else:
        await message.answer("⚠️ That is not an image. Send a photo, or tap Cancel.")
        return

    await state.clear()
    try:
        buf = await message.bot.download(file_id)
        raw = buf.read()
    except Exception as exc:
        log.error("product_photo_download_failed", product_id=pid, error=str(exc))
        await message.answer("⚠️ Could not download that photo from Telegram. Please try again.")
        return

    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p is None:
            await message.answer("Product not found.")
            return
        try:
            asset = await file_storage.store_image(session, raw, message.from_user.id)
        except file_storage.ImageRejected as exc:
            await message.answer(f"⚠️ {exc}\n\nPlease try again from the product menu.")
            return
        p.image_id = asset.id
        await _log_photo_change(session, p, "product_photo_set", message.from_user.id)
        name, stored = p.name, asset.byte_size

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back to product", callback_data=f"padmin:view:{pid}")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await message.answer_photo(
        file_id,
        caption=(
            f"✅ Photo saved for <b>{name}</b> ({stored // 1024} KB stored).\n"
            "It is now live on the website."
        ),
        reply_markup=kb.as_markup(),
    )


@router.message(ProductAdminFlow.photo_wait)
async def photo_wrong_type(message: Message) -> None:
    """Anything that is not a photo/document while we're waiting for one."""
    await message.answer("⚠️ Send a photo of the product, or tap Cancel on the message above.")


@router.callback_query(F.data.startswith("padmin:photodel:"))
async def remove_photo(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    pid = call.data.split("padmin:photodel:", 1)[1]
    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p and p.image_id:
            # The MediaAsset row is left in place — it may be shared with another
            # product via sha256 dedup. Only the link is cleared.
            p.image_id = None
            await _log_photo_change(session, p, "product_photo_removed", call.from_user.id)
    await _show_product(call, UUID(pid))
    await call.answer("Photo removed ✅")


# ── Price history ─────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("padmin:hist:"))
async def price_history(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    pid = UUID(call.data.split("padmin:hist:", 1)[1])
    async with get_session() as session:
        rows = (
            await session.execute(
                select(PriceHistory).where(PriceHistory.product_id == pid)
                .order_by(PriceHistory.created_at.desc()).limit(15)
            )
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=f"padmin:view:{pid}")
    if not rows:
        await call.message.edit_text("🕘 No price history for this product yet.", reply_markup=kb.as_markup())
    else:
        lines = ["🕘 <b>Price history</b>\n"]
        for r in rows:
            when = r.created_at.strftime("%m-%d %H:%M")
            lines.append(f"{when} · {r.field}: {r.old_value} → {r.new_value}")
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup())
    await call.answer()
