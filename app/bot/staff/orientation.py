"""Weekly orientation handlers.

- /orientation (staff:orientation): show this week's COMPUTED topic + the PA's worked
  example. The PA (set_meeting_example) can add/edit the example but never the topic.
  The System Owner (swap_meeting_topic) can swap the computed topic, recording a reason.
- /orientationtopics (manage_orientation_topics, System Owner): list rotation topics,
  toggle active, add a topic. Mirrors the riders list/toggle/add pattern.

The topic is computed from the calendar (app.services.orientation), never typed. Any
inactive topic the rotation skips is audited via log_topic_skips - never silent.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.staff.states import OrientationFlow
from app.core.db import get_session
from app.core.security import get_admin_id, get_role_keys, has, log_activity
from app.core.timeutil import lagos_today
from app.models import OrientationTopic
from app.services import orientation

router = Router(name="staff-orientation")


async def _this_week_meeting(session):
    """Ensure the current week's meeting exists with the computed topic; audit skips.

    Returns (meeting, chosen_topic_or_None).
    """
    on = lagos_today()
    monday = orientation.monday_of(on)
    chosen, skipped = await orientation.computed_topic(session, on)
    if skipped:
        await orientation.log_topic_skips(session, on, skipped)
    meeting = await orientation.ensure_week_meeting(session, monday, chosen.id if chosen else None)
    return meeting, chosen


def _view_kb(role_keys: set[str]) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    if has(role_keys, "set_meeting_example"):
        kb.button(text="✍️ Add / edit example", callback_data="ori:example")
    if has(role_keys, "swap_meeting_topic"):
        kb.button(text="🔄 Swap topic", callback_data="ori:swap")
    if has(role_keys, "manage_orientation_topics"):
        kb.button(text="🗂 Manage topics", callback_data="staff:oritopics")
    kb.button(text="⬅️ Back", callback_data="staff:home")
    kb.adjust(1)
    return kb


async def _show_orientation(target: Message, telegram_id: int) -> None:
    role_keys = await get_role_keys(telegram_id)
    if not (has(role_keys, "set_meeting_example") or has(role_keys, "swap_meeting_topic")
            or has(role_keys, "view_checklist_status") or has(role_keys, "manage_orientation_topics")):
        return
    async with get_session() as session:
        meeting, chosen = await _this_week_meeting(session)
        topic_text = chosen.topic_text if chosen else "⚠️ No active topic in the rotation."
        example = meeting.example_text
    lines = [
        "🎓 <b>This week's orientation</b>",
        f"Week of {meeting.meeting_date.isoformat()}",
        "",
        f"<b>Topic:</b> {topic_text}",
        f"<b>Example:</b> {example}" if example else "<b>Example:</b> <i>not set yet</i>",
    ]
    await target.answer("\n".join(lines), reply_markup=_view_kb(role_keys).as_markup())


@router.message(F.text.regexp(r"^/orientation(@\w+)?(\s|$)"))
async def orientation_cmd(message: Message) -> None:
    await _show_orientation(message, message.from_user.id)


@router.callback_query(F.data == "staff:orientation")
async def orientation_menu(call: CallbackQuery) -> None:
    await _show_orientation(call.message, call.from_user.id)
    await call.answer()


# ── PA: set the worked example ───────────────────────────────────────────────

@router.callback_query(F.data == "ori:example")
async def example_start(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "set_meeting_example"):
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        meeting, _ = await _this_week_meeting(session)
        mid = str(meeting.id)
    await state.set_state(OrientationFlow.example)
    await state.update_data(meeting_id=mid)
    await call.message.answer(
        "Send this week's <b>real worked example</b> for the topic "
        "(a concrete case from the week — the topic itself is fixed)."
    )
    await call.answer()


@router.message(OrientationFlow.example, F.text)
async def example_capture(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    data = await state.get_data()
    await state.clear()
    if not has(role_keys, "set_meeting_example"):
        return
    mid = data.get("meeting_id")
    if not mid:
        return
    actor = await get_admin_id(message.from_user.id)
    async with get_session() as session:
        result = await orientation.set_example(session, UUID(mid), actor, message.text.strip())
    if result is None:
        await message.answer("Couldn't find this week's meeting. Try /orientation again.")
        return
    await log_activity(message.from_user.id, role_keys, "orientation_example_set", "meeting", mid)
    await message.answer("✅ Example saved.")
    await _show_orientation(message, message.from_user.id)


# ── Owner: swap the computed topic ───────────────────────────────────────────

@router.callback_query(F.data == "ori:swap")
async def swap_start(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "swap_meeting_topic"):
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        meeting, _ = await _this_week_meeting(session)
        mid = str(meeting.id)
        topics = await orientation._ordered_topics(session)
    await state.update_data(meeting_id=mid)
    kb = InlineKeyboardBuilder()
    for t in topics:
        if t.active:
            kb.button(text=t.topic_text[:60], callback_data=f"ori:swapto:{t.id}")
    kb.button(text="⬅️ Cancel", callback_data="staff:orientation")
    kb.adjust(1)
    await call.message.answer("Pick the replacement topic for this week:", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("ori:swapto:"))
async def swap_pick(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "swap_meeting_topic"):
        await call.answer("Not authorised.", show_alert=True)
        return
    await state.update_data(new_topic_id=call.data.split("ori:swapto:", 1)[1])
    await state.set_state(OrientationFlow.swap_reason)
    await call.message.answer("Why are you swapping this week's topic? Send a short reason (it is logged).")
    await call.answer()


@router.message(OrientationFlow.swap_reason, F.text)
async def swap_capture(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    data = await state.get_data()
    await state.clear()
    if not has(role_keys, "swap_meeting_topic"):
        return
    mid, new_topic = data.get("meeting_id"), data.get("new_topic_id")
    if not mid or not new_topic:
        return
    actor = await get_admin_id(message.from_user.id)
    async with get_session() as session:
        result = await orientation.swap_topic(
            session, UUID(mid), UUID(new_topic), actor, message.text.strip()
        )
    if result is None:
        await message.answer("Couldn't find this week's meeting. Try /orientation again.")
        return
    await log_activity(message.from_user.id, role_keys, "orientation_topic_swapped", "meeting", mid)
    await message.answer("✅ Topic swapped for this week.")
    await _show_orientation(message, message.from_user.id)


# ── Owner: manage rotation topics ────────────────────────────────────────────

def _topics_kb(topics) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for t in topics:
        flag = "🟢" if t.active else "🔴"
        action = "off" if t.active else "on"
        kb.button(text=f"{flag} {t.topic_text[:50]}", callback_data=f"orit:{action}:{t.id}")
    kb.button(text="➕ Add topic", callback_data="orit:add")
    kb.button(text="⬅️ Back", callback_data="staff:orientation")
    kb.adjust(1)
    return kb


async def _manage_gate(obj) -> set[str] | None:
    role_keys = await get_role_keys(obj.from_user.id)
    return role_keys if has(role_keys, "manage_orientation_topics") else None


@router.message(F.text.regexp(r"^/orientationtopics(@\w+)?(\s|$)"))
async def topics_cmd(message: Message) -> None:
    if await _manage_gate(message) is None:
        return
    await _show_topics(message)


@router.callback_query(F.data == "staff:oritopics")
async def topics_menu(call: CallbackQuery) -> None:
    if await _manage_gate(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    await _show_topics(call.message)
    await call.answer()


async def _show_topics(target: Message) -> None:
    from sqlalchemy import select

    async with get_session() as session:
        topics = (
            await session.execute(select(OrientationTopic).order_by(OrientationTopic.sort_order))
        ).scalars().all()
    text = "🗂 <b>Orientation topics</b>\n\nTap to activate/deactivate."
    await target.answer(text, reply_markup=_topics_kb(topics).as_markup())


async def _set_active(call: CallbackQuery, tid: UUID, active: bool) -> None:
    role_keys = await _manage_gate(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        ok = await orientation.set_topic_active(session, tid, active)
    if not ok:
        await call.answer("Not found.", show_alert=True)
        return
    await log_activity(call.from_user.id, role_keys,
                       "orientation_topic_activated" if active else "orientation_topic_deactivated",
                       "orientation_topic", str(tid))
    await _show_topics(call.message)
    await call.answer()


@router.callback_query(F.data.startswith("orit:on:"))
async def topic_on(call: CallbackQuery) -> None:
    await _set_active(call, UUID(call.data.split("orit:on:", 1)[1]), True)


@router.callback_query(F.data.startswith("orit:off:"))
async def topic_off(call: CallbackQuery) -> None:
    await _set_active(call, UUID(call.data.split("orit:off:", 1)[1]), False)


@router.callback_query(F.data == "orit:add")
async def topic_add_start(call: CallbackQuery, state: FSMContext) -> None:
    if await _manage_gate(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    await state.set_state(OrientationFlow.add_topic)
    await call.message.answer("Send the new topic text. It is added at the end of the rotation.")
    await call.answer()


@router.message(OrientationFlow.add_topic, F.text)
async def topic_add_capture(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    await state.clear()
    if not has(role_keys, "manage_orientation_topics"):
        return
    async with get_session() as session:
        topic = await orientation.add_topic(session, message.text.strip())
        tid = topic.id
    await log_activity(message.from_user.id, role_keys, "orientation_topic_added",
                       "orientation_topic", str(tid))
    await message.answer("✅ Topic added.")
    await _show_topics(message)
