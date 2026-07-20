"""Staff checklist + meeting-tracker handlers.

- /checklist : the caller's items for today, with Done / Skip buttons (own-only).
- /status    : AGGREGATE counts in a group; per-person in private for holders of
               view_checklist_status (PA / owner), else the caller's own summary.
- /meeting   : open a meeting record for today (record_decision holders).
- /decision  : record a decision (System Owner). The text is scanned for phone
               numbers before saving - a hit returns a rephrase prompt, never posts.

Completion always goes through app.services.checklist.complete_item, which appends a
new row (never mutates) and writes an audit record; the DB CHECK is the backstop for
the own-only rule.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.staff.states import ChecklistFlow, DecisionFlow
from app.core.db import get_session
from app.core.security import get_admin_id, get_role_keys, has, log_activity
from app.core.timeutil import lagos_today
from app.models import AdminUser, Meeting, MeetingDecision
from app.services import checklist
from app.services.checklist_messages import build_group_status
from app.services.decision_scan import scan_for_contact

router = Router(name="staff-checklist")

_STATUS_EMOJI = {"pending": "⬜", "done": "✅", "skipped": "⏭"}


# ── /checklist ───────────────────────────────────────────────────────────────

def _checklist_kb(items) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for template, inst in items:
        if inst.status == "pending":
            kb.button(text=f"✅ {template.item_text}", callback_data=f"ckl:done:{inst.id}")
            kb.button(text=f"⏭ Skip", callback_data=f"ckl:skip:{inst.id}")
    kb.button(text="⬅️ Back", callback_data="staff:home")
    kb.adjust(1)
    return kb


def _render_checklist(items) -> str:
    if not items:
        return "🗒 <b>My checklist</b>\n\nNothing scheduled for you today. 🎉"
    lines = ["🗒 <b>My checklist</b>", ""]
    for template, inst in items:
        lines.append(f"{_STATUS_EMOJI.get(inst.status, '•')} {template.item_text}")
    done = sum(1 for _, i in items if i.status == "done")
    lines.append("")
    lines.append(f"<i>{done} of {len(items)} done.</i>")
    return "\n".join(lines)


async def _show_checklist(target: Message, telegram_id: int) -> None:
    role_keys = await get_role_keys(telegram_id)
    if not has(role_keys, "complete_own_checklist"):
        await target.answer("You have no checklist.")
        return
    admin_id = await get_admin_id(telegram_id)
    if admin_id is None:
        await target.answer("You have no checklist.")
        return
    async with get_session() as session:
        items = await checklist.latest_states(session, admin_id, lagos_today())
    await target.answer(_render_checklist(items), reply_markup=_checklist_kb(items).as_markup())


@router.message(F.text.regexp(r"^/checklist(@\w+)?(\s|$)"))
async def checklist_cmd(message: Message) -> None:
    await _show_checklist(message, message.from_user.id)


@router.callback_query(F.data == "staff:checklist")
async def checklist_menu(call: CallbackQuery) -> None:
    await _show_checklist(call.message, call.from_user.id)
    await call.answer()


@router.callback_query(F.data.startswith("ckl:done:"))
async def tick_done(call: CallbackQuery) -> None:
    admin_id = await get_admin_id(call.from_user.id)
    if admin_id is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    inst_id = UUID(call.data.split("ckl:done:", 1)[1])
    async with get_session() as session:
        result = await checklist.complete_item(session, inst_id, admin_id, "done")
    if result is None:
        await call.answer("That isn't your item.", show_alert=True)
        return
    await log_activity(call.from_user.id, await get_role_keys(call.from_user.id), "checklist_done",
                       "checklist_instance", str(result.id))
    await _rerender(call, admin_id)
    await call.answer("Done ✅")


@router.callback_query(F.data.startswith("ckl:skip:"))
async def skip_start(call: CallbackQuery, state: FSMContext) -> None:
    admin_id = await get_admin_id(call.from_user.id)
    if admin_id is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    inst_id = call.data.split("ckl:skip:", 1)[1]
    await state.set_state(ChecklistFlow.skip_reason)
    await state.update_data(instance_id=inst_id)
    await call.message.answer("Why are you skipping this item? Send a short reason.")
    await call.answer()


@router.message(ChecklistFlow.skip_reason, F.text)
async def skip_capture(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    admin_id = await get_admin_id(message.from_user.id)
    inst_id = data.get("instance_id")
    if admin_id is None or not inst_id:
        return
    async with get_session() as session:
        result = await checklist.complete_item(
            session, UUID(inst_id), admin_id, "skipped", skip_reason=message.text.strip()
        )
    if result is None:
        await message.answer("That isn't your item.")
        return
    await log_activity(message.from_user.id, await get_role_keys(message.from_user.id),
                       "checklist_skipped", "checklist_instance", str(result.id))
    await _show_checklist(message, message.from_user.id)


async def _rerender(call: CallbackQuery, admin_id: UUID) -> None:
    async with get_session() as session:
        items = await checklist.latest_states(session, admin_id, lagos_today())
    try:
        await call.message.edit_text(_render_checklist(items), reply_markup=_checklist_kb(items).as_markup())
    except Exception:  # noqa: BLE001 - message unchanged / too old to edit
        pass


# ── /status ──────────────────────────────────────────────────────────────────

async def _status_text(chat_type: str, telegram_id: int) -> str:
    on = lagos_today()
    role_keys = await get_role_keys(telegram_id)
    async with get_session() as session:
        if chat_type in ("group", "supergroup"):
            return build_group_status(await checklist.aggregate_status(session, on))
        if has(role_keys, "view_checklist_status"):
            people = await checklist.per_person_status(session, on)
            if not people:
                return "📋 <b>Team status</b>\n\nNothing scheduled today."
            lines = ["📋 <b>Team status</b>", ""]
            for p in people:
                lines.append(f"• <b>{p['name']}</b>: {p['done']}/{p['total']}")
                for item, reason in p["skipped"]:
                    lines.append(f"    ⏭ {item} — {reason or 'no reason'}")
            return "\n".join(lines)
        # A regular staffer sees ONLY their own count, never the team's.
        admin_id = await get_admin_id(telegram_id, session)
        if admin_id is None:
            return "You have no checklist."
        items = await checklist.latest_states(session, admin_id, on)
        done = sum(1 for _, i in items if i.status == "done")
        return f"🗒 <b>My status</b>\n\n{done} of {len(items)} done today."


@router.message(F.text.regexp(r"^/status(@\w+)?(\s|$)"))
async def status_cmd(message: Message) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not role_keys:
        return
    await message.answer(await _status_text(message.chat.type, message.from_user.id))


@router.callback_query(F.data == "staff:status")
async def status_menu(call: CallbackQuery) -> None:
    await call.message.answer(await _status_text(call.message.chat.type, call.from_user.id))
    await call.answer()


# ── /meeting ─────────────────────────────────────────────────────────────────

@router.message(F.text.regexp(r"^/meeting(@\w+)?(\s|$)"))
async def meeting_cmd(message: Message) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "record_decision"):
        return
    admin_id = await get_admin_id(message.from_user.id)
    async with get_session() as session:
        session.add(Meeting(meeting_date=lagos_today(), chaired_by=admin_id))
    await log_activity(message.from_user.id, role_keys, "meeting_opened", "meeting")
    await message.answer(
        "🗓 Meeting opened for today. Record decisions with /decision.\n"
        "Reminder: do not include phone numbers in a decision."
    )


# ── /decision ────────────────────────────────────────────────────────────────

@router.message(F.text.regexp(r"^/decision(@\w+)?(\s|$)"))
async def decision_cmd(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "record_decision"):
        return
    await state.set_state(DecisionFlow.text)
    await message.answer(
        "📝 Send the decision as one message.\n"
        "<i>Do not include phone numbers — decisions are shared with the whole team.</i>"
    )


@router.message(DecisionFlow.text, F.text)
async def decision_text(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if scan_for_contact(text):
        await message.answer(
            "⚠️ That looks like it contains a phone number. Decisions are posted to the "
            "staff group, so please rephrase without any contact number and resend."
        )
        return  # stay in DecisionFlow.text
    await state.update_data(text=text)
    await state.set_state(DecisionFlow.owner)
    async with get_session() as session:
        admins = (
            await session.execute(select(AdminUser).where(AdminUser.is_active.is_(True)))
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    for a in admins:
        kb.button(text=a.full_name or f"admin:{a.telegram_id}", callback_data=f"dec:owner:{a.id}")
    kb.button(text="No owner", callback_data="dec:noowner")
    kb.adjust(1)
    await message.answer("Who owns this decision?", reply_markup=kb.as_markup())


@router.callback_query(DecisionFlow.owner, F.data.startswith("dec:owner:"))
async def decision_owner(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(owner_id=call.data.split("dec:owner:", 1)[1])
    await state.set_state(DecisionFlow.due)
    await call.message.answer("Due date? Send it as YYYY-MM-DD, or send <b>none</b>.")
    await call.answer()


@router.callback_query(DecisionFlow.owner, F.data == "dec:noowner")
async def decision_no_owner(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(owner_id=None)
    await state.set_state(DecisionFlow.due)
    await call.message.answer("Due date? Send it as YYYY-MM-DD, or send <b>none</b>.")
    await call.answer()


@router.message(DecisionFlow.due, F.text)
async def decision_due(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    raw = message.text.strip().lower()
    due: date | None = None
    if raw not in ("none", "-", "no"):
        try:
            due = date.fromisoformat(raw)
        except ValueError:
            await message.answer("I couldn't read that date. Decision not saved — run /decision again.")
            return
    role_keys = await get_role_keys(message.from_user.id)
    owner_id = data.get("owner_id")
    async with get_session() as session:
        row = MeetingDecision(
            decision_text=data["text"],
            owner_user_id=UUID(owner_id) if owner_id else None,
            due_date=due,
            status="open",
        )
        session.add(row)
        await session.flush()
        did = row.id
    await log_activity(message.from_user.id, role_keys, "decision_recorded", "meeting_decision", str(did))
    await message.answer("✅ Decision recorded.")
