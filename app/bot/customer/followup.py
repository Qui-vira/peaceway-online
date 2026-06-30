"""Handlers for the 24-hour post-delivery follow-up buttons."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.keyboards.customer import back_to_menu

router = Router(name="customer-followup")


@router.callback_query(F.data == "fu:ok")
async def followup_ok(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "🙏 Wonderful! Thank you for choosing Peaceway Online. Stay healthy!",
        reply_markup=back_to_menu(),
    )
    await call.answer()


async def _render_followup_help(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "🆘 We're sorry to hear that. Please describe the issue and our team will assist you right away.",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "fu:help")
async def followup_help(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(call, state, source="follow_up", resume=lambda: _render_followup_help(call)):
        return
    await _render_followup_help(call)


async def _render_followup_pharmacist(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "🧑‍⚕️ Our pharmacist will reach out. You can also type your question here now.",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "fu:pharm")
async def followup_pharmacist(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(
        call, state, source="follow_up", resume=lambda: _render_followup_pharmacist(call)
    ):
        return
    await _render_followup_pharmacist(call)
