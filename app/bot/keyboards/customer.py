"""Inline keyboards for the customer-facing flows."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Order Medicine", callback_data="menu:order")
    kb.button(text="💬 Ask the Pharmacist", callback_data="menu:ask")
    kb.button(text="📍 Check Delivery Areas", callback_data="menu:areas")
    kb.button(text="⭐ Popular Products", callback_data="menu:popular")
    kb.button(text="🧑‍⚕️ Speak to a Human", callback_data="menu:human")
    kb.button(text="📦 Track My Order", callback_data="menu:track")
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    return kb.as_markup()


def back_cancel(back_cb: str = "menu:home") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=back_cb)
    kb.button(text="❌ Cancel", callback_data="menu:home")
    kb.adjust(2)
    return kb.as_markup()


def confirm_button(_: InlineKeyboardMarkup | None = None) -> InlineKeyboardMarkup:  # placeholder for later flows
    return back_to_menu()
