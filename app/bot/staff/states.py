"""FSM states for staff flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StaffFlow(StatesGroup):
    assign_rider = State()      # capture "Rider name, phone"
    message_customer = State()  # capture free-text message to forward
