"""Scan-to-Update: photo -> barcode/OCR -> fuzzy match -> human confirm -> padmin:view.

All mutations go through the existing padmin: product-admin handlers so price/stock
changes always write price_history + audit_logs (no duplicated logic here).
"""
from __future__ import annotations

import io
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, PhotoSize
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has, log_activity
from app.models import Product, ProductScanAttempt
from app.services import scan as scan_service

router = Router(name="staff-scan")
log = get_logger("staff-scan")


class ScanFlow(StatesGroup):
    waiting_photo = State()
    confirm_link = State()  # barcode detected, unmatched -> pick product to link


async def _guard(event) -> set[str] | None:
    role_keys = await get_role_keys(event.from_user.id)
    if not has(role_keys, "view_all_products"):
        return None
    return role_keys


# ── Entry ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "padmin:scan")
async def start_scan(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    await state.set_state(ScanFlow.waiting_photo)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Cancel", callback_data="staff:products")
    await call.message.edit_text(
        "📷 <b>Scan Product</b>\n\n"
        "Send a clear photo of the product's barcode or label. "
        "Make sure the barcode (if present) fills most of the frame.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


# ── Photo received ────────────────────────────────────────────────────────────

@router.message(ScanFlow.waiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext) -> None:
    role_keys = await _guard(message)
    if role_keys is None:
        return

    await message.answer("🔍 Processing image...")

    # Download the highest-res photo.
    photo: PhotoSize = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=buf)
    image_bytes = buf.getvalue()

    # 1. Try barcode decode.
    barcode = scan_service.decode_barcode(image_bytes)
    barcode_matched_product = None

    if barcode:
        async with get_session() as session:
            ident = await scan_service.find_by_barcode(session, barcode)
            if ident:
                barcode_matched_product = await session.get(Product, ident.product_id)

    # 2. Run OCR (always, for fallback or when barcode unmatched).
    ocr_text = await scan_service.run_ocr(image_bytes)

    # 3. Fuzzy match candidates.
    candidates = []
    if not barcode_matched_product:
        query = ocr_text if ocr_text else (barcode or "")
        if query:
            async with get_session() as session:
                candidates = await scan_service.fuzzy_candidates(session, query)

    # 4. Record the attempt.
    attempt_status = (
        "matched" if barcode_matched_product
        else ("unmatched" if barcode else ("pending" if candidates else "failed"))
    )
    async with get_session() as session:
        await scan_service.record_attempt(
            session,
            admin_id=message.from_user.id,
            image_file_id=photo.file_id,
            detected_barcode=barcode,
            extracted_text=ocr_text or None,
            matched_product_ids=[str(c.id) for c in candidates] if candidates else None,
            selected_product_id=barcode_matched_product.id if barcode_matched_product else None,
            status=attempt_status,
        )

    # 5. Show result.
    if barcode_matched_product:
        # Direct match: send straight to product admin view.
        p = barcode_matched_product
        await state.clear()
        kb = InlineKeyboardBuilder()
        kb.button(text=f"✅ Open {p.name[:35]}", callback_data=f"padmin:view:{p.id}")
        kb.button(text="🔎 Search Instead", callback_data="padmin:search")
        kb.button(text="⬅️ Back", callback_data="staff:products")
        kb.adjust(1)
        await message.answer(
            f"✅ Barcode matched: <b>{p.name}</b>\n\nOpen it to update price, stock, etc.",
            reply_markup=kb.as_markup(),
        )
        await log_activity(message.from_user.id, role_keys, "scan_matched", "product", str(p.id))
        return

    if barcode and not barcode_matched_product:
        # Barcode detected but not linked yet.
        await state.update_data(pending_barcode=barcode, scan_file_id=photo.file_id)

    if candidates:
        await _show_candidates(message, state, candidates, barcode=barcode, ocr_text=ocr_text)
        return

    # No barcode, no candidates.
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="📷 Try Again (clearer photo)", callback_data="padmin:scan")
    kb.button(text="🔎 Search Manually", callback_data="padmin:search")
    kb.button(text="📝 Submit Product Request", callback_data="staff:products")
    kb.adjust(1)
    detail = f"Detected barcode: <code>{barcode}</code>\n" if barcode else ""
    await message.answer(
        f"🤔 {detail}Could not match a product from this scan.\n\n"
        "Try a clearer photo, or search manually.",
        reply_markup=kb.as_markup(),
    )


async def _show_candidates(
    message: Message,
    state: FSMContext,
    candidates: list[Product],
    *,
    barcode: str | None,
    ocr_text: str | None,
) -> None:
    kb = InlineKeyboardBuilder()
    for p in candidates:
        price = ""
        if p.pricing and p.pricing.selling_price:
            price = f" · ₦{p.pricing.selling_price:,.0f}"
        kb.button(text=f"{p.name[:40]}{price}", callback_data=f"scan:pick:{p.id}")
    kb.button(text="📷 Try Again (clearer photo)", callback_data="padmin:scan")
    kb.button(text="🔎 Search Manually", callback_data="padmin:search")
    kb.button(text="⬅️ Cancel", callback_data="staff:products")
    kb.adjust(1)
    header = "🔍 <b>Possible matches from scan:</b>"
    if barcode:
        header += f"\nDetected barcode: <code>{barcode}</code>"
    if ocr_text:
        header += f"\nOCR text: <i>{ocr_text[:60]}</i>"
    await message.answer(header, reply_markup=kb.as_markup())


# ── Admin picks a candidate ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("scan:pick:"))
async def pick_candidate(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return

    pid = UUID(call.data.split("scan:pick:", 1)[1])
    data = await state.get_data()
    pending_barcode: str | None = data.get("pending_barcode")
    await state.clear()

    # If there's a pending barcode, offer to link it.
    if pending_barcode:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔗 Yes, link this barcode", callback_data=f"scan:link:{pending_barcode}:{pid}")
        kb.button(text="Skip (open without linking)", callback_data=f"padmin:view:{pid}")
        kb.button(text="⬅️ Cancel", callback_data="staff:products")
        kb.adjust(1)
        async with get_session() as session:
            product = await session.get(Product, pid)
        pname = product.name if product else str(pid)
        await call.message.edit_text(
            f"Link barcode <code>{pending_barcode}</code> to <b>{pname}</b>?\n\n"
            "This makes future scans of this barcode jump straight to the product.",
            reply_markup=kb.as_markup(),
        )
        await call.answer()
    else:
        # No barcode — just go straight to product view.
        from app.bot.staff.products import _show_product
        await _show_product(call, pid)
        await call.answer()


# ── Confirm barcode link ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("scan:link:"))
async def confirm_link(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return

    _, _, barcode, pid_s = call.data.split(":", 3)
    pid = UUID(pid_s)

    async with get_session() as session:
        await scan_service.link_barcode(session, pid, barcode, call.from_user.id)

    await log_activity(call.from_user.id, role_keys, "scan_link_barcode", "product", pid_s)
    await call.answer("Barcode linked ✅")
    from app.bot.staff.products import _show_product
    await _show_product(call, pid)
