"""Soft email-capture gate.

Call `ensure_email(...)` at the top of any customer entry point that should
check for an email before proceeding. If the customer already has one, it
returns True immediately. If not, it shows Add Email / Skip for Now / Main
Menu, and resumes the original action (not Main Menu) once the customer adds
an email or explicitly skips.

The pending "resume" action is kept in an in-process dict keyed by chat id —
this has the same single-process reliability characteristics as the existing
aiogram MemoryStorage FSM (both reset on a process restart; nothing here is
less durable than what's already in production).
"""
from __future__ import annotations

from typing import Awaitable, Callable

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.customer.states import EmailGateFlow
from app.core.db import get_session
from app.services.customers import HIGH_VALUE_SOURCES, get_or_create_customer, is_valid_email, save_email

router = Router(name="customer-email-gate")

_PENDING_RESUME: dict[int, Callable[[], Awaitable[None]]] = {}
_SKIPPED_SOFT: set[int] = set()

PROMPT = (
    "📧 Please add your email so Peaceway can send order updates, request "
    "updates, receipts, and important pharmacy follow-ups."
)
INVALID_EMAIL = (
    "That email does not look correct. Please enter a valid email like name@example.com."
)


def _chat_id(event: CallbackQuery | Message) -> int:
    return event.message.chat.id if isinstance(event, CallbackQuery) else event.chat.id


def _gate_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✉️ Add Email", callback_data="emailgate:add")
    kb.button(text="⏭ Skip for Now", callback_data="emailgate:skip")
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


async def ensure_email(
    event: CallbackQuery | Message,
    state: FSMContext,
    *,
    source: str,
    resume: Callable[[], Awaitable[None]],
) -> bool:
    """Returns True if the caller should proceed now. Otherwise shows the gate
    and arranges for `resume` to run after the customer adds/skips an email —
    the caller must `return` immediately when this returns False."""
    telegram_id = event.from_user.id
    async with get_session() as session:
        customer = await get_or_create_customer(session, telegram_id, event.from_user.full_name)
        has_email = bool(customer.email)

    if has_email:
        return True

    chat_id = _chat_id(event)
    if source not in HIGH_VALUE_SOURCES and chat_id in _SKIPPED_SOFT:
        return True

    _PENDING_RESUME[chat_id] = resume
    await state.set_state(EmailGateFlow.waiting_email)
    await state.update_data(email_gate_source=source)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(PROMPT, reply_markup=_gate_kb())
        await event.answer()
    else:
        await event.answer(PROMPT, reply_markup=_gate_kb())
    return False


async def _resume(chat_id: int) -> None:
    fn = _PENDING_RESUME.pop(chat_id, None)
    if fn is not None:
        await fn()


@router.callback_query(F.data == "emailgate:add")
async def ask_for_email(call: CallbackQuery) -> None:
    await call.message.edit_text("📧 Please type your email address.")
    await call.answer()


@router.message(EmailGateFlow.waiting_email, F.text)
async def got_email(message: Message, state: FSMContext) -> None:
    email = message.text.strip()
    if not is_valid_email(email):
        await message.answer(INVALID_EMAIL)
        return
    data = await state.get_data()
    source = data.get("email_gate_source", "support")
    await state.clear()

    async with get_session() as session:
        customer = await get_or_create_customer(session, message.from_user.id, message.from_user.full_name)
        await save_email(session, customer, email, source, message.from_user.id)

    await message.answer("✅ Thank you. Your email has been saved.")
    await _resume(message.chat.id)


@router.callback_query(F.data == "emailgate:skip")
async def skip_email(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    source = data.get("email_gate_source", "support")
    await state.clear()
    if source not in HIGH_VALUE_SOURCES:
        _SKIPPED_SOFT.add(call.message.chat.id)
    await call.answer()
    await _resume(call.message.chat.id)
