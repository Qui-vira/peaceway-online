"""Staff review of scraped manufacturer product images.

Two taps, not one. The first says "this looks like the right product"; the second
answers a specific question — does the pack size match — because pack size is the one
field the matcher deliberately never checked. A reflexive single Approve on a
medicine photo is exactly the failure this gate exists to prevent.

The image is downloaded with httpx, not Scrapling: scrapling/curl_cffi are dev-only
tools for scripts/, and .railwayignore keeps that whole tree out of the container.
"""
from __future__ import annotations

from html import escape
from uuid import UUID

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has
from app.models import ImageCandidate, Product
from app.services import catalog, image_candidates as svc
from app.services.file_storage import ImageRejected
from app.services.image_matching import BASIS_BRAND_FORM

router = Router(name="staff-image-candidates")
log = get_logger(__name__)

DOWNLOAD_TIMEOUT = 40.0
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "edit_pricing"):
        await call.answer("Not authorised to manage products.", show_alert=True)
        return None
    return role_keys


async def _download(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                log.error("candidate_image_http_error", url=url, status=resp.status_code)
                return None
            if len(resp.content) > MAX_DOWNLOAD_BYTES:
                log.error("candidate_image_too_large", url=url, size=len(resp.content))
                return None
            return resp.content
    except Exception as exc:
        log.error("candidate_image_download_failed", url=url, error=str(exc))
        return None


def _e(value) -> str:
    """HTML-escape a value for Telegram's HTML parse mode.

    Everything shown here is either a scraped string or a free-text catalogue field.
    An unescaped "<" makes Telegram reject the ENTIRE message, and because the
    callback then errors after the tap, the button looks dead rather than broken.
    That is exactly what happened: match_basis contained the literal "pack=<none>",
    Telegram read "<none>" as an unknown tag, and the review flow stopped responding.
    """
    return escape(str(value))


def _review_text(c: ImageCandidate, p: Product) -> str:
    weak = (c.match_basis or "").startswith(BASIS_BRAND_FORM)
    return (
        f"🖼 <b>Image candidate</b>"
        + ("\n⚠️ <b>Brand + form only — strength NOT verified</b>" if weak else "")
        + "\n\n"
        f"<b>Product in our catalogue</b>\n"
        f"{_e(p.name)}\n"
        f"Brand: {_e(p.brand_name or '—')} · Form: {_e(p.dosage_form or '—')}\n"
        f"Strength: {_e(p.strength or '—')} · Pack: <b>{_e(p.pack_size or '— not recorded')}</b>\n\n"
        f"<b>What the manufacturer published</b>\n"
        f"{_e(c.scraped_title)}\n"
        f"Pack on their page: <b>{_e(c.scraped_pack_size or '— none given')}</b>\n\n"
        f"<b>Why these were paired</b>\n"
        f"<code>{_e(c.match_basis or '—')}</code>\n\n"
        f"Source: {_e(c.manufacturer)}"
    )


def _review_kb(c: ImageCandidate):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Looks right", callback_data=f"imgc:confirm:{c.id}")
    kb.button(text="❌ Reject", callback_data=f"imgc:reject:{c.id}")
    kb.button(text="⏭ Skip", callback_data=f"imgc:skip:{c.id}")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "imgc:home")
async def home(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    await state.update_data(imgc_skipped=[])
    async with get_session() as session:
        count = await svc.pending_count(session)

    kb = InlineKeyboardBuilder()
    if count:
        kb.button(text="➡️ Start reviewing", callback_data="imgc:next")
    kb.button(text="⬅️ Back", callback_data="staff:products")
    kb.adjust(1)
    await call.message.edit_text(
        "🖼 <b>Review Image Candidates</b>\n\n"
        f"<b>{count}</b> awaiting review.\n\n"
        "These are photographs taken from the manufacturer's own website and paired "
        "with our products by an exact match on brand, strength and dosage form.\n\n"
        "⚠️ <b>Pack size was NOT matched automatically.</b> You confirm that.\n\n"
        "If the photo shows a different pack from what we dispense, reject it."
        if count else
        "🖼 <b>Review Image Candidates</b>\n\nNothing awaiting review.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "imgc:next")
async def next_candidate(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    data = await state.get_data()
    skipped = {UUID(s) for s in data.get("imgc_skipped", [])}

    async with get_session() as session:
        c = await svc.next_pending(session, skip_ids=skipped)
        if c is None:
            kb = InlineKeyboardBuilder()
            kb.button(text="⬅️ Back", callback_data="imgc:home")
            await call.message.edit_text(
                "✅ <b>Queue clear.</b>\n\nNothing left to review "
                "(minus anything you skipped this session).",
                reply_markup=kb.as_markup(),
            )
            await call.answer()
            return
        p = await catalog.get_product(session, c.product_id)
        text, kb = _review_text(c, p), _review_kb(c)
        image_url = c.image_url

    await call.answer("Loading image…")
    data_bytes = await _download(image_url)
    if data_bytes is None:
        await call.message.edit_text(
            f"{text}\n\n⚠️ <b>Could not download the image.</b> "
            "Reject it or skip — do not approve what you cannot see.",
            reply_markup=kb,
        )
        return

    # Send the photo as a fresh message so the reviewer actually looks at it.
    await call.message.answer_photo(
        BufferedInputFile(data_bytes, filename="candidate.jpg"),
        caption=text,
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("imgc:skip:"))
async def skip(call: CallbackQuery, state: FSMContext) -> None:
    if await _guard(call) is None:
        return
    cid = call.data.split("imgc:skip:", 1)[1]
    data = await state.get_data()
    skipped = list(data.get("imgc_skipped", []))
    if cid not in skipped:
        skipped.append(cid)
    await state.update_data(imgc_skipped=skipped)
    await next_candidate(call, state)


@router.callback_query(F.data.startswith("imgc:confirm:"))
async def confirm_pack_size(call: CallbackQuery) -> None:
    """Second gate. Nothing is written here — this only asks the question.

    Candidates matched on brand+form alone (most manufacturers publish neither a
    registration number nor a comparable strength) get a THIRD gate for strength,
    because that is the field the matcher could not check and the one where being
    wrong is a dosing error.
    """
    if await _guard(call) is None:
        return
    cid = UUID(call.data.split("imgc:confirm:", 1)[1])

    async with get_session() as session:
        c = await svc.get_candidate(session, cid)
        if c is None or c.status != "pending":
            await call.answer("This candidate is no longer pending.", show_alert=True)
            return
        p = await catalog.get_product(session, c.product_id)
        ours = p.pack_size or "— not recorded"
        theirs = c.scraped_pack_size or "— none given"
        needs_strength = (c.match_basis or "").startswith(BASIS_BRAND_FORM)
        our_strength = p.strength or "— not recorded"
        their_strength = c.scraped_strength or "— not published"

    kb = InlineKeyboardBuilder()
    # Strength unverified -> the next tap asks about strength, not publish.
    next_step = f"imgc:strength:{cid}" if needs_strength else f"imgc:approve:{cid}"
    kb.button(
        text=("➡️ Next check — strength" if needs_strength else "✅ Yes — pack size matches"),
        callback_data=next_step,
    )
    kb.button(text="❌ No — reject this image", callback_data=f"imgc:reject:{cid}")
    kb.button(text="⏭ Skip for now", callback_data=f"imgc:skip:{cid}")
    kb.adjust(1)

    await call.message.answer(
        "🔍 <b>Check before this goes live.</b>\n\n"
        "The automatic match did <b>not</b> compare pack size.\n\n"
        f"Our catalogue says: <b>{_e(ours)}</b>\n"
        f"Their page says: <b>{_e(theirs)}</b>\n\n"
        "Look at the photograph again. Does it show the pack we actually dispense?\n\n"
        "If our pack size is not recorded, check the physical pack before answering."
        + (
            f"\n\n⚠️ <b>Strength was also not matched</b> for this one — "
            f"there is one more question after this."
            if needs_strength else ""
        ),
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("imgc:strength:"))
async def confirm_strength(call: CallbackQuery) -> None:
    """Third gate, only for brand+form matches. Writes nothing."""
    if await _guard(call) is None:
        return
    cid = UUID(call.data.split("imgc:strength:", 1)[1])

    async with get_session() as session:
        c = await svc.get_candidate(session, cid)
        if c is None or c.status != "pending":
            await call.answer("This candidate is no longer pending.", show_alert=True)
            return
        p = await catalog.get_product(session, c.product_id)
        ours = p.strength or "— not recorded"
        theirs = c.scraped_strength or "— not published on their page"
        name = p.name

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Yes — strength matches the pack", callback_data=f"imgc:approve:{cid}")
    kb.button(text="❌ No — reject this image", callback_data=f"imgc:reject:{cid}")
    kb.button(text="⏭ Skip for now", callback_data=f"imgc:skip:{cid}")
    kb.adjust(1)

    await call.message.answer(
        "⚠️ <b>Strength check — this one was not matched automatically.</b>\n\n"
        f"<b>{_e(name)}</b>\n\n"
        f"Our catalogue: <b>{_e(ours)}</b>\n"
        f"Their page: <b>{_e(theirs)}</b>\n\n"
        "This photo was paired on brand and dosage form only. Manufacturers write "
        "strength differently from us, so the system could not compare it.\n\n"
        "<b>Read the strength printed on the pack in the photo.</b> Is it the same "
        "medicine at the same strength we dispense?\n\n"
        "If you are not certain, reject. A wrong strength on a medicine photo is a "
        "dosing error.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("imgc:approve:"))
async def approve(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    cid = UUID(call.data.split("imgc:approve:", 1)[1])

    async with get_session() as session:
        c = await svc.get_candidate(session, cid)
        if c is None:
            await call.answer("Candidate not found.", show_alert=True)
            return
        image_url = c.image_url

    data_bytes = await _download(image_url)
    if data_bytes is None:
        await call.answer("Could not download the image. Nothing was changed.", show_alert=True)
        return

    async with get_session() as session:
        c = await svc.get_candidate(session, cid)
        try:
            product = await svc.approve(session, c, data_bytes, call.from_user.id)
            name = product.name
        except (svc.CandidateNotReviewable, ImageRejected) as exc:
            await call.answer(str(exc), show_alert=True)
            return

    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Next candidate", callback_data="imgc:next")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text(
        f"✅ <b>Published.</b>\n\n<b>{_e(name)}</b> now shows this photo on the website.\n\n"
        "Source and match basis were recorded against the image.",
        reply_markup=kb.as_markup(),
    )
    await call.answer("Approved ✅")


@router.callback_query(F.data.startswith("imgc:reject:"))
async def reject(call: CallbackQuery) -> None:
    if await _guard(call) is None:
        return
    cid = UUID(call.data.split("imgc:reject:", 1)[1])

    async with get_session() as session:
        c = await svc.get_candidate(session, cid)
        if c is None:
            await call.answer("Candidate not found.", show_alert=True)
            return
        try:
            await svc.reject(session, c, call.from_user.id, reason="staff review")
        except svc.CandidateNotReviewable as exc:
            await call.answer(str(exc), show_alert=True)
            return

    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Next candidate", callback_data="imgc:next")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text(
        "❌ <b>Rejected.</b>\n\nThe product keeps its current image, and this "
        "candidate will not be offered again.",
        reply_markup=kb.as_markup(),
    )
    await call.answer("Rejected")
