"""Staff flow for backfilling product descriptive data, one product at a time.

Why this exists: 41 of the 51 listed products were created by hand through the
"create from name" path and carry manufacturer NULL, blank brand_name, blank
dosage_form, and a pack size sitting in the `strength` column ("200ml", "1000ml",
"130g"). That breaks search, category filtering, prescription logic, and makes any
exact-match image pipeline impossible — there is nothing to match on.

Nothing here is auto-populated. Every value is typed by a staff member looking at the
physical pack. Parsing "Chemiron Blood Tonic 1000ml" into brand + pack size is
inference, and inference on medicine data is exactly what we refuse to do: a wrong
dosage form or strength on a NAFDAC-regulated product is a patient-safety problem,
not a data-tidiness one.

Writes go through products_admin.apply_change(), so every edit lands in price_history
and admin_activity_logs alongside price changes.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.staff.states import ProductBackfillFlow
from app.core.db import get_session
from app.core.security import get_role_keys, has
from app.models import Product
from app.services import catalog
from app.services.products_admin import (
    DESCRIPTIVE_FIELDS,
    REQUIRED_BACKFILL_FIELDS,
    apply_change,
    backfill_stats,
    missing_backfill_fields,
    next_backfill_product,
)

router = Router(name="staff-products-backfill")

# Order shown to staff — brand first because it anchors everything else.
_FIELD_ORDER = ("brand_name", "manufacturer", "dosage_form", "strength", "pack_size")

_HINTS = {
    "brand_name": "The brand as printed on the pack, e.g. <code>Chemiron</code>",
    "manufacturer": "Company on the pack, e.g. <code>Afrab-Chem Limited</code>",
    "dosage_form": "e.g. <code>Syrup</code>, <code>Tablet</code>, <code>Lotion</code>, <code>Capsule</code>",
    "strength": "Active ingredient strength ONLY, e.g. <code>500 mg</code> or <code>5 mg/5 mL</code>",
    "pack_size": "How much is in the box, e.g. <code>100 mL</code>, <code>30 capsules</code>, <code>10*10</code>",
}


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "edit_pricing"):
        await call.answer("Not authorised to manage products.", show_alert=True)
        return None
    return role_keys


def _detail_text(p: Product) -> str:
    missing = missing_backfill_fields(p)

    def row(field: str) -> str:
        label = DESCRIPTIVE_FIELDS[field][0]
        val = (getattr(p, field) or "").strip()
        mark = "⚠️" if field in missing else ("✅" if val else "·")
        return f"{mark} {label}: <b>{val or '—'}</b>"

    lines = [f"🧩 <b>{p.name}</b>", ""]
    lines += [row(f) for f in _FIELD_ORDER]
    lines.append("")
    if missing:
        lines.append(f"Missing {len(missing)} of {len(REQUIRED_BACKFILL_FIELDS)} required fields.")
    else:
        lines.append("All required fields present ✅")
    lines.append("\nCheck the physical pack. Do not guess.")
    return "\n".join(lines)


def _detail_kb(p: Product):
    kb = InlineKeyboardBuilder()
    missing = set(missing_backfill_fields(p))
    for field in _FIELD_ORDER:
        label = DESCRIPTIVE_FIELDS[field][0]
        prefix = "⚠️" if field in missing else "✏️"
        kb.button(text=f"{prefix} {label}", callback_data=f"pbf:set:{field}:{p.id}")
    kb.button(text="⏭ Skip this product", callback_data=f"pbf:skip:{p.id}")
    kb.button(text="➡️ Next product", callback_data="pbf:next")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    return kb.as_markup()


async def _show(target, product: Product, state: FSMContext) -> None:
    await state.update_data(product_id=str(product.id))
    text, kb = _detail_text(product), _detail_kb(product)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data == "pbf:home")
async def backfill_home(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    await state.clear()
    async with get_session() as session:
        listed = await backfill_stats(session, listed_only=True)
        everything = await backfill_stats(session, listed_only=False)

    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Start / Next product", callback_data="pbf:next")
    kb.button(text="⬅️ Back", callback_data="staff:products")
    kb.adjust(1)
    await call.message.edit_text(
        "🧩 <b>Backfill Product Data</b>\n\n"
        f"<b>Listed products</b> (visible to customers)\n"
        f"  {listed['complete']} of {listed['total']} complete · "
        f"<b>{listed['pending']} need data</b>\n\n"
        f"<b>Whole catalogue</b>\n"
        f"  {everything['complete']:,} of {everything['total']:,} complete · "
        f"{everything['pending']:,} need data\n\n"
        "Required: Brand, Manufacturer, Dosage form, Pack size.\n"
        "Strength is optional — some products genuinely have none.\n\n"
        "Listed products are served first. Work from the physical pack.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "pbf:next")
async def next_product(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    data = await state.get_data()
    skipped = {UUID(s) for s in data.get("skipped", [])}

    async with get_session() as session:
        p = await next_backfill_product(session, listed_only=True, skip_ids=skipped)
        scope = "listed"
        if p is None:
            p = await next_backfill_product(session, listed_only=False, skip_ids=skipped)
            scope = "catalogue"
        if p is None:
            kb = InlineKeyboardBuilder()
            kb.button(text="⬅️ Back", callback_data="pbf:home")
            await call.message.edit_text(
                "✅ <b>Nothing left in the queue.</b>\n\n"
                "Every product (minus any you skipped this session) has Brand, "
                "Manufacturer, Dosage form and Pack size.",
                reply_markup=kb.as_markup(),
            )
            await call.answer()
            return
        await _show(call, p, state)

    await call.answer(f"Next from {scope}")


@router.callback_query(F.data.startswith("pbf:skip:"))
async def skip_product(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    pid = call.data.split("pbf:skip:", 1)[1]
    data = await state.get_data()
    skipped = list(data.get("skipped", []))
    if pid not in skipped:
        skipped.append(pid)
    await state.update_data(skipped=skipped)
    await next_product(call, state)


@router.callback_query(F.data.startswith("pbf:set:"))
async def ask_field(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    _, _, field, pid = call.data.split(":", 3)
    if field not in DESCRIPTIVE_FIELDS:
        await call.answer("Unknown field.", show_alert=True)
        return

    label = DESCRIPTIVE_FIELDS[field][0]
    await state.set_state(ProductBackfillFlow.value)
    await state.update_data(field=field, product_id=pid)

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Cancel", callback_data=f"pbf:view:{pid}")
    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        current = (getattr(p, field) or "—") if p else "—"

    await call.message.edit_text(
        f"✏️ <b>{label}</b>\n\n"
        f"{_HINTS[field]}\n\n"
        f"Current value: <b>{current}</b>\n\n"
        "Send the new value, or <code>-</code> to clear it.\n"
        "Read it off the pack — do not guess.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.message(ProductBackfillFlow.value, F.text)
async def got_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field, pid = data.get("field"), data.get("product_id")
    await state.set_state(None)

    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p is None:
            await message.answer("Product not found.")
            return
        try:
            summary = await apply_change(session, p, field, message.text, message.from_user.id,
                                         reason="staff backfill")
        except ValueError as exc:
            await message.answer(f"⚠️ {exc}\n\nSend the value again, or tap Cancel above.")
            await state.set_state(ProductBackfillFlow.value)
            return
        await session.refresh(p)
        await message.answer(f"✅ {summary}")
        await _show(message, p, state)


@router.callback_query(F.data.startswith("pbf:view:"))
async def view_product(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    pid = call.data.split("pbf:view:", 1)[1]
    await state.set_state(None)
    async with get_session() as session:
        p = await catalog.get_product(session, UUID(pid))
        if p is None:
            await call.answer("Product not found.", show_alert=True)
            return
        await _show(call, p, state)
    await call.answer()
