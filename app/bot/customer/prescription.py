"""Prescription upload flow: accept image/PDF, save a record, alert pharmacists."""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.customer.states import PrescriptionFlow
from app.bot.keyboards.customer import back_cancel, back_to_menu
from app.core import rbac
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import Prescription, Product
from app.services.customers import get_or_create_customer
from app.services.email import send_email
from app.services.rbac_service import recipients_for_roles

router = Router(name="customer-prescription")
log = get_logger("prescription")

CONFIRMATION = (
    "✅ Prescription received. A Peaceway pharmacist will review it and reply shortly."
)

_VALID_DOC_EXT = (".pdf", ".jpg", ".jpeg", ".png")


async def _render_upload_prompt(call: CallbackQuery, state: FSMContext, product_id: str | None, origin: str) -> None:
    await state.set_state(PrescriptionFlow.waiting_file)
    await state.update_data(rx_product_id=product_id, rx_origin=origin)
    await call.message.edit_text(
        "📄 <b>Upload Prescription</b>\n\nSend a clear photo or PDF of your prescription.",
        reply_markup=back_cancel(origin),
    )
    await call.answer()


@router.callback_query(F.data.startswith("rx:"))
async def start_upload(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    raw = call.data.split("rx:", 1)[1]
    product_id = None if raw == "-" else raw
    origin = f"prod:{product_id}" if product_id else "menu:home"
    if not await ensure_email(
        call, state, source="prescription",
        resume=lambda: _render_upload_prompt(call, state, product_id, origin),
    ):
        return
    await _render_upload_prompt(call, state, product_id, origin)


@router.message(PrescriptionFlow.waiting_file, F.photo | F.document)
async def got_file(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = data.get("rx_product_id")
    await state.clear()

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "image"
    else:
        doc = message.document
        name_ok = (doc.file_name or "").lower().endswith(_VALID_DOC_EXT)
        mime_ok = doc.mime_type in ("application/pdf", "image/jpeg", "image/png")
        if not (name_ok or mime_ok):
            await message.answer("Please send the prescription as an image or PDF file.")
            return
        file_id = doc.file_id
        file_type = "document"

    async with get_session() as session:
        customer = await get_or_create_customer(session, message.from_user.id, message.from_user.full_name)

        product_name = None
        if product_id:
            p = await session.get(Product, UUID(product_id))
            product_name = p.name if p else None

        session.add(
            Prescription(
                customer_id=customer.id,
                product_id=UUID(product_id) if product_id else None,
                file_id=file_id,
                file_type=file_type,
            )
        )
        cust_name, cust_tid = customer.full_name, customer.telegram_id

    try:
        await _alert_pharmacists(message.bot, cust_name, cust_tid, product_name)
    except Exception as exc:  # noqa: BLE001
        log.error("rx_alert_failed", error=str(exc))

    await message.answer(CONFIRMATION, reply_markup=back_to_menu())


@router.message(PrescriptionFlow.waiting_file)
async def not_a_file(message: Message) -> None:
    await message.answer("Please send the prescription as a photo or PDF document.")


async def _alert_pharmacists(bot, cust_name, cust_tid, product_name) -> None:
    telegram_ids, emails = await recipients_for_roles(
        {rbac.LEAD_PHARMACIST, rbac.PHARMACIST_ADMIN, rbac.SYSTEM_OWNER}
    )
    extra = f" for <b>{product_name}</b>" if product_name else ""
    text = (
        f"📄 <b>New prescription uploaded</b>{extra}\n"
        f"From: {cust_name or 'customer'} (id <code>{cust_tid}</code>)\n\n"
        "Open Pharmacist Inbox → Prescriptions to review."
    )
    for tid in telegram_ids:
        try:
            await bot.send_message(tid, text)
        except Exception:  # noqa: BLE001
            continue

    plain = text.replace("<b>", "").replace("</b>", "")
    from app.core.config import get_settings

    await send_email(emails, f"[{get_settings().pharmacy_name}] New prescription uploaded", plain)
