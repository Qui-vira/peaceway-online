"""Inline keyboards for the customer-facing flows."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    """Main menu as a 2-column grid (callbacks unchanged). Renders identically on
    mobile and desktop Telegram."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Order Medicine", callback_data="menu:order"),
                InlineKeyboardButton(text="💬 Ask Pharmacist", callback_data="menu:ask"),
            ],
            [
                InlineKeyboardButton(text="📍 Delivery Areas", callback_data="menu:areas"),
                InlineKeyboardButton(text="⭐ Popular Products", callback_data="menu:popular"),
            ],
            [
                InlineKeyboardButton(text="👨‍⚕️ Speak to Support", callback_data="menu:human"),
                InlineKeyboardButton(text="📦 Track Order", callback_data="menu:track"),
            ],
            [
                InlineKeyboardButton(text="📋 How It Works", callback_data="menu:how"),
                InlineKeyboardButton(text="👤 My Profile", callback_data="menu:profile"),
            ],
            [
                InlineKeyboardButton(text="📝 Track My Requests", callback_data="menu:track_requests"),
            ],
        ]
    )


def help_menu() -> InlineKeyboardMarkup:
    """/help quick actions in the same 2-column grid style."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 How It Works", callback_data="menu:how"),
                InlineKeyboardButton(text="🛒 Order Medicine", callback_data="menu:order"),
            ],
            [
                InlineKeyboardButton(text="💬 Ask Pharmacist", callback_data="menu:ask"),
                InlineKeyboardButton(text="📦 Track Order", callback_data="menu:track"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:home"),
            ],
        ]
    )


def how_it_works_menu() -> InlineKeyboardMarkup:
    """How It Works quick actions, same grid style."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Order Medicine", callback_data="menu:order"),
                InlineKeyboardButton(text="📍 Delivery Areas", callback_data="menu:areas"),
            ],
            [
                InlineKeyboardButton(text="💬 Ask Pharmacist", callback_data="menu:ask"),
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:home"),
            ],
        ]
    )


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
