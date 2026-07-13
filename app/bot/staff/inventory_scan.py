"""Staff "Scan Stock From Photos": batch AI inventory intake inside Telegram.

Flow (spec: agentic inventory intake):
  1. Products menu -> 🤖 Scan Stock From Photos (permission: scan_inventory)
  2. Pick a scan mode (full count / new stock / draft)
  3. Send photos (any number; albums supported; duplicates ignored)
  4. Tap "Analyse Photos" -> vision provider analyses the whole batch
  5. Review / correct / skip items; export CSV
  6. Explicit "Confirm Inventory Update" -> single-transaction commit + audit

Sessions live in the DB (inventory_scan_sessions), so a bot restart loses only
the in-memory FSM routing — the scan itself can be resumed from the menu.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.staff.states import InventoryScanFlow
from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has, log_activity
from app.models import Product
from app.models.inventory_scan import (
    ACTION_REVIEW,
    REVIEW_CONFIRMED,
    REVIEW_EDITED,
    REVIEW_PENDING,
    REVIEW_SKIPPED,
    SCAN_MODE_ADD,
    SCAN_MODE_DRAFT,
    SCAN_MODE_SET,
    SCAN_STATUS_ANALYSING,
    SCAN_STATUS_COLLECTING,
    SCAN_STATUS_REVIEW,
    InventoryScanItem,
    InventoryScanSession,
)
from app.services import catalog as catalog_service
from app.services import inventory_scan as scan_service
from app.services.inventory_vision import (
    VisionProviderError,
    get_provider,
)
from app.services.inventory_vision.base import ScanImage
from app.services.products_admin import VALID_CATEGORIES

router = Router(name="staff-inventory-scan")
log = get_logger("staff-inventory-scan")

MODE_LABELS = {
    SCAN_MODE_SET: "Full stock count",
    SCAN_MODE_ADD: "New stock received",
    SCAN_MODE_DRAFT: "Photo inventory draft",
}
_STATUS_EMOJI = {
    REVIEW_PENDING: "🕒",
    REVIEW_CONFIRMED: "✅",
    REVIEW_EDITED: "✏️",
    REVIEW_SKIPPED: "⏭",
}
_LEVEL_LABEL = {"high": "High", "medium": "Medium", "low": "Low"}
PAGE_SIZE = 8


async def _guard(event) -> set[str] | None:
    role_keys = await get_role_keys(event.from_user.id)
    if not has(role_keys, "scan_inventory"):
        return None
    return role_keys


async def _deny(call: CallbackQuery) -> None:
    await call.answer("Not authorised for inventory scanning.", show_alert=True)


async def _load_scan(db, scan_id: UUID | str) -> InventoryScanSession | None:
    try:
        sid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
    except ValueError:
        return None
    return await db.get(InventoryScanSession, sid)


async def _load_item(db, item_id: str) -> tuple[InventoryScanItem, InventoryScanSession] | None:
    try:
        iid = UUID(item_id)
    except ValueError:
        return None
    item = await db.get(InventoryScanItem, iid)
    if item is None:
        return None
    scan = await db.get(InventoryScanSession, item.session_id)
    if scan is None:
        return None
    return item, scan


# ── Entry / mode selection ───────────────────────────────────────────────────

def _mode_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔢 Full stock count (replace stock)", callback_data="invscan:mode:set")
    kb.button(text="📦 New stock received (add to stock)", callback_data="invscan:mode:add")
    kb.button(text="📝 Photo inventory draft (no changes)", callback_data="invscan:mode:draft")
    kb.button(text="⬅️ Back", callback_data="staff:products")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "invscan:start")
async def start_scan(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await _deny(call)
        return
    if not get_settings().inventory_scan_enabled:
        await call.answer(
            "AI scanning is not configured yet (ANTHROPIC_API_KEY is missing).",
            show_alert=True,
        )
        return

    async with get_session() as db:
        active = await scan_service.get_active_session(db, call.from_user.id)
        active_id = str(active.id) if active else None
        active_status = active.status if active else None
        active_photos = len(active.images) if active else 0

    if active_id:
        kb = InlineKeyboardBuilder()
        kb.button(text="▶️ Resume that scan", callback_data=f"invscan:resume:{active_id}")
        kb.button(text="🗑 Discard it & start fresh", callback_data=f"invscan:discard:{active_id}")
        kb.button(text="⬅️ Back", callback_data="staff:products")
        kb.adjust(1)
        state_txt = {
            SCAN_STATUS_COLLECTING: f"collecting photos ({active_photos} so far)",
            SCAN_STATUS_ANALYSING: "being analysed",
            SCAN_STATUS_REVIEW: "waiting for your review",
        }.get(active_status, active_status)
        await call.message.edit_text(
            f"📷 You already have a scan in progress — it is {state_txt}.\n\n"
            "Resume it, or discard it and start a new one?",
            reply_markup=kb.as_markup(),
        )
        await call.answer()
        return

    await call.message.edit_text(
        "🤖 <b>Scan Stock From Photos</b>\n\n"
        "First, choose what this scan is for:\n\n"
        "🔢 <b>Full stock count</b> — the counted quantity <i>replaces</i> the current "
        "stock for each confirmed product.\n"
        "📦 <b>New stock received</b> — the counted quantity is <i>added</i> to the "
        "current stock.\n"
        "📝 <b>Photo inventory draft</b> — review + CSV only, no stock changes.",
        reply_markup=_mode_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("invscan:discard:"))
async def discard_and_restart(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await _load_scan(db, call.data.split(":", 2)[2])
        if scan and scan.admin_telegram_id == call.from_user.id:
            await scan_service.cancel_scan(db, scan)
    await state.clear()
    await call.message.edit_text(
        "🤖 <b>Scan Stock From Photos</b>\n\nChoose what this scan is for:",
        reply_markup=_mode_kb(),
    )
    await call.answer("Previous scan discarded.")


@router.callback_query(F.data.startswith("invscan:resume:"))
async def resume_scan(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await _load_scan(db, call.data.split(":", 2)[2])
        if scan is None or scan.admin_telegram_id != call.from_user.id:
            await call.answer("Scan not found.", show_alert=True)
            return
        if scan.status in (SCAN_STATUS_COLLECTING, SCAN_STATUS_ANALYSING):
            scan.status = SCAN_STATUS_COLLECTING
            await state.set_state(InventoryScanFlow.collecting)
            await state.update_data(scan_id=str(scan.id))
            await call.message.edit_text(
                _collect_text(scan.scan_mode, len(scan.images)),
                reply_markup=_collect_kb(),
            )
        else:  # awaiting_review
            text, kb = await _summary_view(db, scan)
            await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("invscan:mode:"))
async def choose_mode(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await _deny(call)
        return
    mode_key = call.data.split(":", 2)[2]
    mode = {"set": SCAN_MODE_SET, "add": SCAN_MODE_ADD, "draft": SCAN_MODE_DRAFT}.get(mode_key)
    if mode is None:
        await call.answer("Unknown mode.", show_alert=True)
        return

    async with get_session() as db:
        scan = await scan_service.create_scan_session(
            db, call.from_user.id, call.message.chat.id, mode
        )
        scan_id = str(scan.id)

    await state.set_state(InventoryScanFlow.collecting)
    await state.update_data(scan_id=scan_id, status_msg_id=None)
    await log_activity(call.from_user.id, role_keys, "inventory_scan_started",
                       "inventory_scan_session", scan_id, detail={"mode": mode})
    await call.message.edit_text(_collect_text(mode, 0), reply_markup=_collect_kb())
    await call.answer()


def _collect_text(mode: str, count: int) -> str:
    line = f"\n\n📷 Photos so far: <b>{count}</b>" if count else ""
    return (
        f"📷 <b>Scan Stock From Photos</b> · <i>{MODE_LABELS.get(mode, mode)}</i>\n\n"
        "Send clear photos of the products or shelves you want me to scan.\n\n"
        "You can send multiple photos (albums work too). Overlapping photos are fine — "
        "I will not count the same items twice.\n\n"
        "When you are finished, tap <b>Analyse Photos</b>." + line
    )


def _collect_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Analyse Photos", callback_data="invscan:analyse")
    kb.button(text="❌ Cancel", callback_data="invscan:cancel")
    kb.adjust(1)
    return kb.as_markup()


# ── Image collection ─────────────────────────────────────────────────────────

async def _accept_upload(
    message: Message, state: FSMContext, file_id: str, file_unique_id: str
) -> None:
    data = await state.get_data()
    scan_id = data.get("scan_id")
    if not scan_id:
        await state.clear()
        return

    settings = get_settings()
    async with get_session() as db:
        scan = await _load_scan(db, scan_id)
        if scan is None or scan.status != SCAN_STATUS_COLLECTING:
            await state.clear()
            await message.answer("This scan is no longer collecting photos. Open Products → Scan Stock From Photos to start again.")
            return
        if len(scan.images) >= settings.inventory_scan_max_images:
            await message.answer(
                f"⚠️ Photo limit reached ({settings.inventory_scan_max_images} per scan). "
                "Tap Analyse Photos, or Cancel and split the shelf into two scans."
            )
            return
        image, total = await scan_service.add_image(
            db, scan, file_id, file_unique_id, message.media_group_id
        )

    if image is None:
        note = f"⚠️ That photo was already added. Photos so far: <b>{total}</b>."
    else:
        note = (
            f"📷 Photo <b>{total}</b> added.\n\n"
            "Send more photos or tap <b>Analyse Photos</b>."
        )

    # Keep a single running status message: drop the previous one (best effort).
    old_id = data.get("status_msg_id")
    if old_id:
        try:
            await message.bot.delete_message(message.chat.id, old_id)
        except Exception:  # noqa: BLE001
            pass
    sent = await message.answer(note, reply_markup=_collect_kb(), disable_notification=True)
    await state.update_data(status_msg_id=sent.message_id)


@router.message(InventoryScanFlow.collecting, F.photo)
async def collect_photo(message: Message, state: FSMContext) -> None:
    if await _guard(message) is None:
        return
    photo = message.photo[-1]  # highest resolution
    await _accept_upload(message, state, photo.file_id, photo.file_unique_id)


@router.message(InventoryScanFlow.collecting, F.document)
async def collect_document(message: Message, state: FSMContext) -> None:
    if await _guard(message) is None:
        return
    doc = message.document
    if (doc.mime_type or "").startswith("image/"):
        await _accept_upload(message, state, doc.file_id, doc.file_unique_id)
    else:
        await message.answer(
            "I can only scan photos (JPG/PNG). Please send product photos, "
            "or tap Cancel to stop.", reply_markup=_collect_kb(),
        )


@router.message(InventoryScanFlow.collecting, F.text)
async def collect_text_hint(message: Message, state: FSMContext) -> None:
    if await _guard(message) is None:
        return
    await message.answer(
        "I'm collecting photos for this scan — no need to describe them. "
        "Send photos, then tap <b>Analyse Photos</b>.", reply_markup=_collect_kb(),
    )


# ── Analysis ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "invscan:analyse")
async def analyse_photos(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await _deny(call)
        return
    data = await state.get_data()
    scan_id = data.get("scan_id")
    if not scan_id:
        async with get_session() as db:
            active = await scan_service.get_active_session(db, call.from_user.id)
            scan_id = str(active.id) if active else None
    if not scan_id:
        await call.answer("No scan in progress.", show_alert=True)
        return

    async with get_session() as db:
        scan = await _load_scan(db, scan_id)
        if scan is None or scan.status not in (SCAN_STATUS_COLLECTING, SCAN_STATUS_ANALYSING):
            await call.answer("This scan can't be analysed right now.", show_alert=True)
            return
        n_images = len(scan.images)
        if n_images == 0:
            await call.answer("Send at least one photo first.", show_alert=True)
            return
        scan.status = SCAN_STATUS_ANALYSING

    await call.message.edit_text(
        f"🔍 Analysing <b>{n_images}</b> photo(s)…\n\n"
        "I'm identifying products, reading labels, and counting stock. "
        "This can take a minute or two — I'll post the results here."
    )
    await call.answer()
    asyncio.create_task(
        _run_analysis_task(call.message.bot, state, scan_id, call.from_user.id, role_keys)
    )


async def _run_analysis_task(
    bot: Bot, state: FSMContext, scan_id: str, user_id: int, role_keys: set[str]
) -> None:
    """Background analysis: download photos, call the provider, build the review."""
    chat_id = None
    try:
        # 1. Download images (per-image failures don't kill the batch).
        async with get_session() as db:
            scan = await _load_scan(db, scan_id)
            if scan is None:
                return
            chat_id = scan.chat_id
            files = [(img.position, img.telegram_file_id) for img in scan.images]

        images: list[ScanImage] = []
        sent_positions: list[int] = []
        failed_positions: list[int] = []
        for position, file_id in files:
            try:
                buf = await bot.download(file_id)
                images.append(ScanImage(data=buf.read(), media_type="image/jpeg"))
                sent_positions.append(position)
            except Exception as exc:  # noqa: BLE001
                log.error("scan_image_download_failed", scan_id=scan_id,
                          position=position, error=str(exc))
                failed_positions.append(position)

        if not images:
            raise VisionProviderError(
                "I couldn't download any of the photos from Telegram.", retryable=True
            )

        # 2. Provider call (stages A+B happen in one batched request).
        provider = get_provider()
        result = await provider.analyse_images(images)

        # 3. Remap provider image indexes back to session positions.
        def _remap(indexes: list[int]) -> list[int]:
            return sorted({sent_positions[i] for i in indexes if 0 <= i < len(sent_positions)})

        result = result.model_copy(
            update={
                "products": [
                    p.model_copy(update={"source_images": _remap(p.source_images)})
                    for p in result.products
                ],
                "unreadable_images": _remap(result.unreadable_images) + failed_positions,
                "warnings": result.warnings
                + (
                    [f"{len(failed_positions)} photo(s) could not be downloaded and were skipped."]
                    if failed_positions
                    else []
                ),
            }
        )

        # 4. Stages B–E + persist review items.
        async with get_session() as db:
            scan = await _load_scan(db, scan_id)
            if scan is None:
                return
            if not result.products:
                scan.status = SCAN_STATUS_COLLECTING
                kb = InlineKeyboardBuilder()
                kb.button(text="🔍 Analyse Again", callback_data="invscan:analyse")
                kb.button(text="❌ Cancel", callback_data="invscan:cancel")
                kb.adjust(1)
                await state.set_state(InventoryScanFlow.collecting)
                await state.update_data(scan_id=scan_id)
                await bot.send_message(
                    chat_id,
                    "🤔 I could not identify any products in these photos.\n\n"
                    "Try clearer, closer photos with readable labels, then tap "
                    "<b>Analyse Again</b>.",
                    reply_markup=kb.as_markup(),
                )
                return
            await scan_service.run_analysis(db, scan, result)
            text, kb = await _summary_view(db, scan)

        await state.clear()
        await log_activity(user_id, role_keys, "inventory_scan_analysed",
                           "inventory_scan_session", scan_id)
        await bot.send_message(chat_id, text, reply_markup=kb)

    except VisionProviderError as exc:
        log.error("scan_analysis_provider_error", scan_id=scan_id, error=str(exc))
        async with get_session() as db:
            scan = await _load_scan(db, scan_id)
            if scan is not None:
                chat_id = chat_id or scan.chat_id
                # Keep the photos; let the user retry or add clearer ones.
                scan.status = SCAN_STATUS_COLLECTING
        await state.set_state(InventoryScanFlow.collecting)
        await state.update_data(scan_id=scan_id)
        kb = InlineKeyboardBuilder()
        kb.button(text="🔁 Try Again", callback_data="invscan:analyse")
        kb.button(text="❌ Cancel", callback_data="invscan:cancel")
        kb.adjust(1)
        if chat_id:
            retry_note = " You can try again in a moment." if exc.retryable else ""
            await bot.send_message(
                chat_id,
                f"⚠️ Analysis failed: {exc}.{retry_note}\n\n"
                "Your photos are kept — you can also add clearer photos before retrying.",
                reply_markup=kb.as_markup(),
            )
    except Exception as exc:  # noqa: BLE001
        log.error("scan_analysis_crashed", scan_id=scan_id, error=str(exc))
        async with get_session() as db:
            scan = await _load_scan(db, scan_id)
            if scan is not None:
                chat_id = chat_id or scan.chat_id
                await scan_service.fail_scan(db, scan, str(exc))
        await state.clear()
        if chat_id:
            await bot.send_message(
                chat_id,
                "❌ Something went wrong while analysing this scan. Nothing was changed "
                "in the inventory. Please start a new scan from Products.",
            )


# ── Review summary ───────────────────────────────────────────────────────────

async def _summary_view(db, scan: InventoryScanSession):
    summary = scan.analysis_summary or {}
    detected = summary.get("detected", len(scan.items))
    existing = summary.get("existing", 0)
    new = summary.get("new", 0)
    needs = summary.get("needs_review", 0)
    reviewed = sum(1 for i in scan.items if i.review_status != REVIEW_PENDING)

    lines = [
        "✅ <b>Inventory Scan Complete</b>",
        "",
        f"Scan mode: <b>{MODE_LABELS.get(scan.scan_mode, scan.scan_mode)}</b>",
        f"Photos: {len(scan.images)} · Products detected: <b>{detected}</b>",
        "",
        f"🗂 Existing products: <b>{existing}</b>",
        f"🆕 New products: <b>{new}</b>",
        f"⚠️ Needs review: <b>{needs}</b>",
        f"👀 Reviewed so far: {reviewed}/{detected}",
    ]
    for w in (scan.warnings or [])[:4]:
        lines.append(f"\n⚠️ <i>{w}</i>")
    if scan.scan_mode == SCAN_MODE_DRAFT:
        lines.append("\n📝 Draft mode: no stock will be changed. Review and export the CSV.")

    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Review All", callback_data="invscan:list:all:0")
    if needs:
        kb.button(text=f"⚠️ Review Uncertain ({needs})", callback_data="invscan:list:unc:0")
    kb.button(text="✅ Confirm All Safe Changes", callback_data="invscan:confirmall")
    kb.button(text="📄 Export CSV", callback_data="invscan:csv")
    if scan.scan_mode == SCAN_MODE_DRAFT:
        kb.button(text="💾 Finish Draft", callback_data="invscan:commit")
    else:
        kb.button(text="💾 Update Inventory…", callback_data="invscan:commit")
    kb.button(text="❌ Cancel Scan", callback_data="invscan:cancel")
    kb.adjust(1)
    return "\n".join(lines), kb.as_markup()


async def _scan_for_user(db, user_id: int, *, status: str = SCAN_STATUS_REVIEW):
    scan = await scan_service.get_active_session(db, user_id)
    if scan is None or scan.status != status:
        return None
    return scan


@router.callback_query(F.data == "invscan:summary")
async def show_summary(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await _scan_for_user(db, call.from_user.id)
        if scan is None:
            await call.answer("No scan awaiting review.", show_alert=True)
            return
        text, kb = await _summary_view(db, scan)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("invscan:list:"))
async def list_items(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    _, _, kind, page_s = call.data.split(":", 3)
    page = int(page_s)
    async with get_session() as db:
        scan = await _scan_for_user(db, call.from_user.id)
        if scan is None:
            await call.answer("No scan awaiting review.", show_alert=True)
            return
        items = scan.items
        if kind == "unc":
            items = [
                i for i in items
                if i.proposed_action == ACTION_REVIEW
                or scan_service.item_confidence_level(i) == "low"
            ]
        total = len(items)
        chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

        kb = InlineKeyboardBuilder()
        for item in chunk:
            emoji = _STATUS_EMOJI.get(item.review_status, "🕒")
            flag = " ⚠️" if item.proposed_action == ACTION_REVIEW else ""
            kb.button(
                text=f"{emoji} {item.product_name[:34]} · qty {item.detected_stock}{flag}",
                callback_data=f"invscan:item:{item.id}",
            )
        nav = []
        if page > 0:
            nav.append(("⬅️ Prev", f"invscan:list:{kind}:{page - 1}"))
        if (page + 1) * PAGE_SIZE < total:
            nav.append(("Next ➡️", f"invscan:list:{kind}:{page + 1}"))
        for text_, cb in nav:
            kb.button(text=text_, callback_data=cb)
        kb.button(text="⬅️ Back to Summary", callback_data="invscan:summary")
        kb.adjust(*([1] * len(chunk) + ([len(nav)] if nav else []) + [1]))

        title = "⚠️ Items needing review" if kind == "unc" else "📋 All detected items"
        await call.message.edit_text(
            f"{title} ({total}):" if total else f"{title}: none 🎉",
            reply_markup=kb.as_markup(),
        )
    await call.answer()


# ── Item card ────────────────────────────────────────────────────────────────

_ACTION_LABEL = {
    "set_stock": "Set stock to {qty}",
    "add_stock": "Add {qty} to stock",
    "create_product": "Create new product",
    "needs_review": "Needs your review",
    "no_change": "No change",
    "draft": "Draft only (no change)",
}
_MATCH_LABEL = {
    "exact_existing": "Existing product",
    "probable_existing": "Possible existing match",
    "new_product": "New product",
    "uncertain": "Uncertain",
}


async def _item_view(db, item: InventoryScanItem, scan: InventoryScanSession):
    current_stock = None
    matched_name = None
    if item.matched_product_id:
        product = await db.get(Product, item.matched_product_id)
        if product:
            matched_name = product.name
            current_stock = product.pricing.stock_qty if product.pricing else 0

    level = scan_service.item_confidence_level(item)
    action = _ACTION_LABEL.get(item.proposed_action, item.proposed_action).format(
        qty=item.detected_stock
    )
    lines = [
        f"💊 <b>{item.product_name}</b>",
        f"Status: {_STATUS_EMOJI.get(item.review_status)} {item.review_status}",
        "",
        f"Detected stock: <b>{item.detected_stock}</b>",
    ]
    if current_stock is not None:
        lines.append(f"Current stock: {current_stock}")
    lines += [
        f"Proposed action: <b>{action}</b>",
        f"Match: {_MATCH_LABEL.get(item.match_type, item.match_type)}"
        + (f" → {matched_name}" if matched_name and matched_name != item.product_name else ""),
        f"Confidence: <b>{_LEVEL_LABEL[level]}</b>",
        "",
        f"Dosage: {item.dosage or '—'}",
        f"Category: {item.category or '—'}",
        f"Prescription: {item.prescription}",
    ]
    if item.description:
        lines.append(f"Description: {item.description[:120]}")
    if item.counting_notes:
        lines.append(f"\n🧮 <i>{item.counting_notes[:250]}</i>")

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Confirm", callback_data=f"invscan:ok:{item.id}")
    kb.button(text="✏️ Edit", callback_data=f"invscan:edit:{item.id}")
    kb.button(text="⏭ Skip", callback_data=f"invscan:skip:{item.id}")
    kb.button(text="🖼 View Source Photo", callback_data=f"invscan:photo:{item.id}")
    kb.button(text="⬅️ Back to List", callback_data="invscan:list:all:0")
    kb.adjust(3, 1, 1)
    return "\n".join(lines), kb.as_markup()


@router.callback_query(F.data.startswith("invscan:item:"))
async def show_item(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    async with get_session() as db:
        loaded = await _load_item(db, call.data.split(":", 2)[2])
        if loaded is None:
            await call.answer("Item not found.", show_alert=True)
            return
        item, scan = loaded
        text, kb = await _item_view(db, item, scan)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("invscan:ok:") | F.data.startswith("invscan:skip:"))
async def confirm_or_skip(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    action, item_id = call.data.split(":", 2)[1:]
    async with get_session() as db:
        loaded = await _load_item(db, item_id)
        if loaded is None:
            await call.answer("Item not found.", show_alert=True)
            return
        item, scan = loaded
        if action == "ok":
            item.review_status = REVIEW_CONFIRMED
            # Confirming a needs_review item is the human decision the plan needed.
            if item.proposed_action == ACTION_REVIEW and scan.scan_mode != SCAN_MODE_DRAFT:
                item.proposed_action = (
                    ("set_stock" if scan.scan_mode == SCAN_MODE_SET else "add_stock")
                    if item.matched_product_id
                    else "create_product"
                )
        else:
            item.review_status = REVIEW_SKIPPED
        text, kb = await _item_view(db, item, scan)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer("Confirmed ✅" if action == "ok" else "Skipped")


@router.callback_query(F.data.startswith("invscan:photo:"))
async def view_photo(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    async with get_session() as db:
        loaded = await _load_item(db, call.data.split(":", 2)[2])
        if loaded is None:
            await call.answer("Item not found.", show_alert=True)
            return
        item, scan = loaded
        positions = item.source_images or []
        by_pos = {img.position: img.telegram_file_id for img in scan.images}
        file_ids = [by_pos[p] for p in positions if p in by_pos][:3]
    if not file_ids:
        await call.answer("No source photo recorded for this item.", show_alert=True)
        return
    for fid in file_ids:
        await call.message.answer_photo(fid, caption=f"Source photo — {item.product_name}"[:1024])
    await call.answer()


# ── Editing ──────────────────────────────────────────────────────────────────

_EDIT_FIELDS = [
    ("Name", "name"), ("Stock", "stock"), ("Dosage", "dosage"),
    ("Category", "cat"), ("Prescription", "rx"), ("Availability", "avail"),
    ("Description", "desc"), ("Cost Price", "cost"), ("Selling Price", "sell"),
    ("Match Product", "match"),
]
_FIELD_MAP = {
    "name": "product_name", "stock": "stock", "dosage": "dosage", "desc": "description",
    "cost": "cost_price", "sell": "selling_price",
}
_PROMPTS = {
    "name": "Type the correct product name:",
    "stock": "Type the correct stock quantity (whole number):",
    "dosage": "Type the dosage/strength (e.g. 500mg), or “-” to clear:",
    "desc": "Type a short description, or “-” to clear:",
    "cost": "Type the cost price (₦):",
    "sell": "Type the selling price (₦):",
}


@router.callback_query(F.data.startswith("invscan:edit:"))
async def edit_menu(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    item_id = call.data.split(":", 2)[2]
    async with get_session() as db:
        loaded = await _load_item(db, item_id)
        if loaded is None:
            await call.answer("Item not found.", show_alert=True)
            return
        item, _ = loaded
        name = item.product_name
    kb = InlineKeyboardBuilder()
    for label, key in _EDIT_FIELDS:
        kb.button(text=label, callback_data=f"invscan:ef:{item_id}:{key}")
    kb.button(text="⬅️ Back", callback_data=f"invscan:item:{item_id}")
    kb.adjust(2, 2, 2, 2, 2, 1)
    await call.message.edit_text(
        f"✏️ <b>Edit {name}</b>\n\nChoose the field to correct:", reply_markup=kb.as_markup()
    )
    await call.answer()


@router.callback_query(F.data.startswith("invscan:ef:"))
async def edit_field(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    _, _, item_id, key = call.data.split(":", 3)

    if key in _PROMPTS:
        await state.set_state(InventoryScanFlow.edit_value)
        await state.update_data(edit_item_id=item_id, edit_field=key)
        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Cancel Edit", callback_data=f"invscan:item:{item_id}")
        await call.message.edit_text(_PROMPTS[key], reply_markup=kb.as_markup())
        await call.answer()
        return

    if key == "cat":
        kb = InlineKeyboardBuilder()
        for i, cat in enumerate(VALID_CATEGORIES):
            kb.button(text=cat, callback_data=f"invscan:setcat:{item_id}:{i}")
        kb.button(text="⬅️ Back", callback_data=f"invscan:edit:{item_id}")
        kb.adjust(2, 2, 2, 1)
        await call.message.edit_text("Choose the category:", reply_markup=kb.as_markup())
        await call.answer()
        return

    if key == "rx":
        kb = InlineKeyboardBuilder()
        for val in ("OTC", "Rx", "uncertain"):
            kb.button(text=val, callback_data=f"invscan:setrx:{item_id}:{val}")
        kb.button(text="⬅️ Back", callback_data=f"invscan:edit:{item_id}")
        kb.adjust(3, 1)
        await call.message.edit_text(
            "Prescription status (choose “uncertain” to leave it for pharmacist review):",
            reply_markup=kb.as_markup(),
        )
        await call.answer()
        return

    if key == "avail":
        async with get_session() as db:
            loaded = await _load_item(db, item_id)
            if loaded is None:
                await call.answer("Item not found.", show_alert=True)
                return
            item, scan = loaded
            await scan_service.apply_correction(
                db, item, "availability", not item.availability, call.from_user.id, scan.scan_mode
            )
            text, kb = await _item_view(db, item, scan)
        await call.message.edit_text(text, reply_markup=kb)
        await call.answer("Availability toggled.")
        return

    if key == "match":
        kb = InlineKeyboardBuilder()
        kb.button(text="🔎 Search catalog", callback_data=f"invscan:matchsearch:{item_id}")
        kb.button(text="🆕 Mark as NEW product", callback_data=f"invscan:setmatch:{item_id}:new")
        kb.button(text="⬅️ Back", callback_data=f"invscan:edit:{item_id}")
        kb.adjust(1)
        await call.message.edit_text(
            "Link this item to a catalog product, or mark it as a brand-new product:",
            reply_markup=kb.as_markup(),
        )
        await call.answer()
        return

    await call.answer("Unknown field.", show_alert=True)


@router.message(InventoryScanFlow.edit_value, F.text)
async def edit_value_input(message: Message, state: FSMContext) -> None:
    if await _guard(message) is None:
        await state.clear()
        return
    data = await state.get_data()
    item_id, key = data.get("edit_item_id"), data.get("edit_field")
    field = _FIELD_MAP.get(key or "")
    if not item_id or not field:
        await state.clear()
        return
    value = message.text.strip()
    if value == "-" and key in ("dosage", "desc"):
        value = ""

    async with get_session() as db:
        loaded = await _load_item(db, item_id)
        if loaded is None:
            await state.clear()
            await message.answer("Item not found any more.")
            return
        item, scan = loaded
        try:
            await scan_service.apply_correction(
                db, item, field, value, message.from_user.id, scan.scan_mode
            )
        except (ValueError, ArithmeticError):
            await message.answer("That value doesn't look right — please try again:")
            return
        text, kb = await _item_view(db, item, scan)
    await state.clear()
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("invscan:setcat:"))
async def set_category(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    _, _, item_id, idx = call.data.split(":", 3)
    try:
        category = VALID_CATEGORIES[int(idx)]
    except (ValueError, IndexError):
        await call.answer("Unknown category.", show_alert=True)
        return
    async with get_session() as db:
        loaded = await _load_item(db, item_id)
        if loaded is None:
            await call.answer("Item not found.", show_alert=True)
            return
        item, scan = loaded
        await scan_service.apply_correction(
            db, item, "category", category, call.from_user.id, scan.scan_mode
        )
        text, kb = await _item_view(db, item, scan)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer(f"Category → {category}")


@router.callback_query(F.data.startswith("invscan:setrx:"))
async def set_prescription(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    _, _, item_id, val = call.data.split(":", 3)
    async with get_session() as db:
        loaded = await _load_item(db, item_id)
        if loaded is None:
            await call.answer("Item not found.", show_alert=True)
            return
        item, scan = loaded
        await scan_service.apply_correction(
            db, item, "prescription", val, call.from_user.id, scan.scan_mode
        )
        text, kb = await _item_view(db, item, scan)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer(f"Prescription → {val}")


@router.callback_query(F.data.startswith("invscan:matchsearch:"))
async def match_search_prompt(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    item_id = call.data.split(":", 2)[2]
    await state.set_state(InventoryScanFlow.match_search)
    await state.update_data(edit_item_id=item_id)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Cancel", callback_data=f"invscan:item:{item_id}")
    await call.message.edit_text(
        "🔎 Type the product name to search the catalog:", reply_markup=kb.as_markup()
    )
    await call.answer()


@router.message(InventoryScanFlow.match_search, F.text)
async def match_search_results(message: Message, state: FSMContext) -> None:
    if await _guard(message) is None:
        await state.clear()
        return
    data = await state.get_data()
    item_id = data.get("edit_item_id")
    if not item_id:
        await state.clear()
        return
    async with get_session() as db:
        results = await catalog_service.search_products(db, message.text, limit=8)
    await state.clear()
    kb = InlineKeyboardBuilder()
    for p in results:
        stock = p.pricing.stock_qty if p.pricing else 0
        kb.button(
            text=f"{p.name[:40]} · stock {stock}",
            callback_data=f"invscan:setmatch:{item_id}:{p.id}",
        )
    kb.button(text="🔎 Search Again", callback_data=f"invscan:matchsearch:{item_id}")
    kb.button(text="⬅️ Back", callback_data=f"invscan:item:{item_id}")
    kb.adjust(1)
    label = f"Results for “{message.text}”:" if results else f"No products found for “{message.text}”."
    await message.answer(label, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("invscan:setmatch:"))
async def set_match(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    _, _, item_id, target = call.data.split(":", 3)
    async with get_session() as db:
        loaded = await _load_item(db, item_id)
        if loaded is None:
            await call.answer("Item not found.", show_alert=True)
            return
        item, scan = loaded
        product = None
        if target != "new":
            try:
                product = await db.get(Product, UUID(target))
            except ValueError:
                product = None
            if product is None:
                await call.answer("Product not found.", show_alert=True)
                return
        await scan_service.set_item_match(db, item, product, call.from_user.id, scan.scan_mode)
        text, kb = await _item_view(db, item, scan)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer("Match updated.")


# ── Bulk confirm / CSV / commit / cancel ─────────────────────────────────────

@router.callback_query(F.data == "invscan:confirmall")
async def confirm_all_safe(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await _scan_for_user(db, call.from_user.id)
        if scan is None:
            await call.answer("No scan awaiting review.", show_alert=True)
            return
        confirmed = scan_service.confirm_safe_items(scan)
        text, kb = await _summary_view(db, scan)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer(
        f"Confirmed {confirmed} high-confidence item(s)." if confirmed
        else "Nothing left that can be auto-confirmed — review the remaining items individually.",
        show_alert=confirmed == 0,
    )


@router.callback_query(F.data == "invscan:csv")
async def export_csv(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await _scan_for_user(db, call.from_user.id)
        if scan is None:
            await call.answer("No scan awaiting review.", show_alert=True)
            return
        csv_text = scan_service.generate_csv(scan)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    file = BufferedInputFile(csv_text.encode("utf-8-sig"), filename=f"inventory_scan_{stamp}.csv")
    await call.message.answer_document(
        file, caption="📄 Reviewed scan export — same format as the CSV importer."
    )
    await call.answer("CSV sent ✅")


@router.callback_query(F.data == "invscan:commit")
async def pre_commit(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await _scan_for_user(db, call.from_user.id)
        if scan is None:
            await call.answer("No scan awaiting review.", show_alert=True)
            return
        plan = scan_service.commit_plan(scan)
        pending = sum(1 for i in scan.items if i.review_status == REVIEW_PENDING)
        mode_label = MODE_LABELS.get(scan.scan_mode, scan.scan_mode)

    # An empty commit would throw the whole review away — block it.
    if plan["update"] + plan["create"] + plan["draft"] == 0:
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Confirm All Safe Changes", callback_data="invscan:confirmall")
        kb.button(text="📋 Review All", callback_data="invscan:list:all:0")
        kb.button(text="⬅️ Back to Summary", callback_data="invscan:summary")
        kb.adjust(1)
        await call.message.edit_text(
            "⚠️ <b>Nothing is confirmed yet.</b>\n\n"
            f"All {plan['skip']} detected item(s) are still unreviewed or skipped, so "
            "updating now would change nothing and close this scan.\n\n"
            "Confirm the items you want applied first — “Confirm All Safe Changes” "
            "handles the high-confidence ones in one tap.",
            reply_markup=kb.as_markup(),
        )
        await call.answer("Confirm at least one item first.", show_alert=True)
        return

    if scan.scan_mode == SCAN_MODE_DRAFT:
        body = (
            "📝 <b>Finish Draft</b>\n\n"
            f"{plan['draft']} reviewed item(s) will be saved to this draft.\n"
            f"{plan['skip']} item(s) will be left out.\n\n"
            "No product stock will be changed."
        )
    else:
        body = (
            "💾 <b>Ready to Update Inventory</b>\n\n"
            f"🗂 {plan['update']} existing product(s) will be updated\n"
            f"🆕 {plan['create']} new product(s) will be created\n"
            f"⏭ {plan['skip']} item(s) will be skipped"
            + (f" (including {pending} not yet reviewed)" if pending else "")
            + f"\n\nScan mode: <b>{mode_label}</b>"
        )
        if pending:
            body += (
                "\n\n⚠️ Unreviewed items are <b>not</b> committed. Go back if you still "
                "want to confirm them."
            )

    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Confirm Inventory Update" if scan.scan_mode != SCAN_MODE_DRAFT else "✅ Finish Draft",
        callback_data="invscan:commitgo",
    )
    kb.button(text="⬅️ Go Back", callback_data="invscan:summary")
    kb.button(text="❌ Cancel Scan", callback_data="invscan:cancel")
    kb.adjust(1)
    await call.message.edit_text(body, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "invscan:commitgo")
async def do_commit(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await _deny(call)
        return
    try:
        async with get_session() as db:
            scan = await _scan_for_user(db, call.from_user.id)
            if scan is None:
                await call.answer("No scan awaiting review.", show_alert=True)
                return
            plan = scan_service.commit_plan(scan)
            if plan["update"] + plan["create"] + plan["draft"] == 0:
                # Stale confirm button: nothing is confirmed, keep the session open.
                text, kb = await _summary_view(db, scan)
                await call.message.edit_text(text, reply_markup=kb)
                await call.answer(
                    "Nothing is confirmed yet — confirm at least one item first.",
                    show_alert=True,
                )
                return
            scan_id = str(scan.id)
            summary = await scan_service.commit_scan_session(db, scan, call.from_user.id)
            mode = scan.scan_mode
    except Exception as exc:  # noqa: BLE001
        # get_session rolled the transaction back: the catalog is untouched.
        log.error("scan_commit_failed", admin=call.from_user.id, error=str(exc))
        kb = InlineKeyboardBuilder()
        kb.button(text="🔁 Try Again", callback_data="invscan:commit")
        kb.button(text="⬅️ Back to Review", callback_data="invscan:summary")
        kb.adjust(1)
        await call.message.edit_text(
            "❌ <b>Update failed — no inventory changes were made.</b>\n\n"
            f"Reason: {str(exc)[:200]}\n\nYou can fix the items and try again.",
            reply_markup=kb.as_markup(),
        )
        await call.answer()
        return

    await state.clear()
    await log_activity(
        call.from_user.id, role_keys, "inventory_scan_committed",
        "inventory_scan_session", scan_id,
        detail={"mode": mode, "updated": summary["updated"], "created": summary["created"],
                "skipped": summary["skipped"]},
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Download CSV", callback_data=f"invscan:donecsv:{scan_id}")
    kb.button(text="💊 Products", callback_data="staff:products")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    if mode == SCAN_MODE_DRAFT:
        text = (
            "📝 <b>Draft saved.</b>\n\n"
            f"{summary['drafted']} item(s) recorded · {summary['skipped']} left out.\n"
            "No stock was changed."
        )
    else:
        text = (
            "✅ <b>Inventory updated.</b>\n\n"
            f"🗂 Updated: <b>{summary['updated']}</b>\n"
            f"🆕 Created: <b>{summary['created']}</b>\n"
            f"⏭ Skipped: <b>{summary['skipped']}</b>\n\n"
            "Every change is recorded in the price history and audit log."
        )
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer("Done ✅")


@router.callback_query(F.data.startswith("invscan:donecsv:"))
async def export_committed_csv(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await _load_scan(db, call.data.split(":", 2)[2])
        if scan is None or scan.admin_telegram_id != call.from_user.id:
            await call.answer("Scan not found.", show_alert=True)
            return
        csv_text = scan_service.generate_csv(scan)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    file = BufferedInputFile(csv_text.encode("utf-8-sig"), filename=f"inventory_scan_{stamp}.csv")
    await call.message.answer_document(file, caption="📄 Committed scan export.")
    await call.answer("CSV sent ✅")


@router.callback_query(F.data == "invscan:cancel")
async def cancel(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await _deny(call)
        return
    async with get_session() as db:
        scan = await scan_service.get_active_session(db, call.from_user.id)
        scan_id = None
        if scan is not None:
            scan_id = str(scan.id)
            await scan_service.cancel_scan(db, scan)
    await state.clear()
    if scan_id:
        await log_activity(call.from_user.id, role_keys, "inventory_scan_cancelled",
                           "inventory_scan_session", scan_id)
    kb = InlineKeyboardBuilder()
    kb.button(text="💊 Products", callback_data="staff:products")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text(
        "❌ Scan cancelled. No inventory changes were made.", reply_markup=kb.as_markup()
    )
    await call.answer()
