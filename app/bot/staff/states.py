"""FSM states for staff flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StaffFlow(StatesGroup):
    assign_rider = State()      # capture "Rider name, phone"
    message_customer = State()  # capture free-text message to forward


class AdminFlow(StatesGroup):
    add_telegram_id = State()   # capture new admin's numeric Telegram ID
    add_role = State()          # choose role (inline)
    add_details = State()       # capture "Full Name, email"
