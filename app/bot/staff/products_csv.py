"""Admin CSV bulk price/stock import.

Matches rows to EXISTING products by normalized name and updates pricing, stock,
category, Rx status, availability, dosage, and description. Rows that match no
existing product are CREATED as new catalog entries. New products start as
review-required (not sellable) unless the row marks them OTC with price + stock.
Dry-run first, then confirm to commit.

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
from app.services.products_admin import apply_csv_row, create_product_from_name
from scripts.import_pharmaos import normalize_name  # reuse name normalization

router = Router(name="staff-products-csv")


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
        "Existing products are updated by name; new names are added to the catalog.\n"
        "New items go live only when the row is marked OTC (prescription) with a "
        "selling price and stock — otherwise they wait for pharmacist review."
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

    matched, to_create = [], []
    seen_new: set[str] = set()  # dedupe brand-new names within this file
    for r in rows:
        key = _norm_key(r["product_name"])
        pid = by_name.get(key)
        if pid:
            matched.append((str(pid), r))
        elif key not in seen_new:
            seen_new.add(key)
            to_create.append((None, r))
        # duplicate new name in the same file → skip the extra row

    # Persist both sets so commit can update matches and create the rest.
    await state.update_data(csv_rows=matched + to_create)
    await state.set_state(ProductAdminFlow.csv_confirm)

    sample_new = "\n".join(f"• {u[1]['product_name']}" for u in to_create[:8])
    text = (
        f"📋 <b>CSV dry run</b>\n\n"
        f"Rows: {len(rows)}\n"
        f"✅ Existing (will update): <b>{len(matched)}</b>\n"
        f"🆕 New (will be added): <b>{len(to_create)}</b>\n"
    )
    if sample_new:
        text += f"\nNew products:\n{sample_new}\n"
    text += "\nApply these changes?"
    kb = InlineKeyboardBuilder()
    kb.button(text=f"✅ Update {len(matched)} · Add {len(to_create)}", callback_data="padmin:csvcommit")
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
    updated = created = 0

    async with get_session() as session:
        for pid, r in rows:
            if pid is None:
                p = await create_product_from_name(
                    session, r["product_name"], admin_id, strength=r.get("dosage") or None
                )
                created += 1
            else:
                p = (await session.execute(select(Product).where(Product.id == pid))).scalar_one_or_none()
                if p is None:
                    continue
                updated += 1
            await apply_csv_row(session, p, r, admin_id)

    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    await call.message.edit_text(
        f"✅ CSV import complete.\nUpdated <b>{updated}</b> · Added <b>{created}</b> products.",
        reply_markup=kb.as_markup(),
    )
    await call.answer("Imported ✅")
