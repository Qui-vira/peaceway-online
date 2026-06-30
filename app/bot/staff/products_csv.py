"""Admin CSV bulk price/stock import.

Matches rows to EXISTING products by normalized name and updates pricing, stock,
category, Rx status, availability, and description. Never creates new products;
unmatched rows are reported for review. Dry-run first, then confirm to commit.

Expected columns (header row, case-insensitive):
  product_name, category, cost_price, selling_price, stock, dosage,
  prescription (OTC/Rx/true/false), availability (yes/no), description
"""
from __future__ import annotations

import csv
import io

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.staff.states import ProductAdminFlow
from app.core.db import get_session
from app.core.security import get_role_keys, has
from app.models import Product
from app.services.products_admin import apply_change, parse_int, parse_money
from scripts.import_pharmaos import normalize_name  # reuse name normalization

router = Router(name="staff-products-csv")

_TRUE = {"rx", "prescription", "prescription-required", "true", "yes", "1", "required"}
_AVAIL_TRUE = {"yes", "true", "1", "available", "in stock", "in_stock"}


async def _guard(event) -> bool:
    role_keys = await get_role_keys(event.from_user.id)
    return has(role_keys, "edit_pricing")


@router.callback_query(F.data == "padmin:csv")
async def ask_csv(call: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(call):
        await call.answer("Not authorised.", show_alert=True)
        return
    await state.set_state(ProductAdminFlow.csv_wait)
    await call.message.edit_text(
        "📤 <b>Import Products (CSV)</b>\n\n"
        "Send a .csv file with a header row including:\n"
        "<code>product_name, category, cost_price, selling_price, stock, dosage, "
        "prescription, availability, description</code>\n\n"
        "Products are matched by name. Unmatched rows are reported, not created."
    )
    await call.answer()


def _norm_key(name: str) -> str:
    return normalize_name(name).lower()


@router.message(ProductAdminFlow.csv_wait, F.document)
async def got_csv(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        await state.clear()
        return
    doc = message.document
    if not (doc.file_name or "").lower().endswith(".csv"):
        await message.answer("Please send a .csv file.")
        return
    buf = await message.bot.download(doc)
    try:
        content = buf.read().decode("utf-8-sig")
    except Exception:  # noqa: BLE001
        await message.answer("Couldn't read the file. Please save it as UTF-8 CSV.")
        return

    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for raw in reader:
        clean = {(k or "").strip().lower().replace(" ", "_"): (v or "").strip() for k, v in raw.items()}
        if clean.get("product_name"):
            rows.append(clean)

    if not rows:
        await message.answer("No data rows found. Check the header row and try again.")
        await state.clear()
        return

    # Match against existing products by normalized name.
    async with get_session() as session:
        products = (await session.execute(select(Product))).scalars().all()
        by_name = {_norm_key(p.name): p.id for p in products}

    matched, unmatched = [], []
    for r in rows:
        pid = by_name.get(_norm_key(r["product_name"]))
        (matched if pid else unmatched).append((str(pid) if pid else None, r))

    await state.update_data(csv_rows=[(pid, r) for pid, r in matched])
    await state.set_state(ProductAdminFlow.csv_confirm)

    sample_unmatched = "\n".join(f"• {u[1]['product_name']}" for u in unmatched[:8])
    text = (
        f"📋 <b>CSV dry run</b>\n\n"
        f"Rows: {len(rows)}\n"
        f"✅ Matched (will update): <b>{len(matched)}</b>\n"
        f"❓ Unmatched (skipped): <b>{len(unmatched)}</b>\n"
    )
    if sample_unmatched:
        text += f"\nUnmatched examples:\n{sample_unmatched}\n"
    text += "\nApply the matched updates?"
    kb = InlineKeyboardBuilder()
    kb.button(text=f"✅ Apply {len(matched)} updates", callback_data="padmin:csvcommit")
    kb.button(text="❌ Cancel", callback_data="staff:products")
    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(ProductAdminFlow.csv_confirm, F.data == "padmin:csvcommit")
async def commit_csv(call: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(call):
        await call.answer("Not authorised.", show_alert=True)
        return
    data = await state.get_data()
    rows = data.get("csv_rows", [])
    await state.clear()
    admin_id = call.from_user.id
    updated = 0

    async with get_session() as session:
        for pid, r in rows:
            p = (await session.execute(select(Product).where(Product.id == pid))).scalar_one_or_none()
            if p is None:
                continue
            if r.get("cost_price") and parse_money(r["cost_price"]) is not None:
                await apply_change(session, p, "cost_price", r["cost_price"], admin_id, reason="CSV import")
            if r.get("selling_price") and parse_money(r["selling_price"]) is not None:
                await apply_change(session, p, "selling_price", r["selling_price"], admin_id, reason="CSV import")
            if r.get("stock") and parse_int(r["stock"]) is not None:
                await apply_change(session, p, "stock", r["stock"], admin_id, reason="CSV import")
            if r.get("category"):
                cat = r["category"].strip().title()
                try:
                    await apply_change(session, p, "category", cat, admin_id, reason="CSV import")
                except ValueError:
                    pass  # unknown category, skip silently
            if r.get("prescription"):
                await apply_change(session, p, "rx", r["prescription"].lower() in _TRUE, admin_id, reason="CSV import")
            if r.get("availability"):
                await apply_change(session, p, "available", r["availability"].lower() in _AVAIL_TRUE, admin_id, reason="CSV import")
            if r.get("description"):
                p.description = r["description"][:1000]
            updated += 1

    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    await call.message.edit_text(f"✅ CSV import complete. Updated <b>{updated}</b> products.", reply_markup=kb.as_markup())
    await call.answer("Imported ✅")
