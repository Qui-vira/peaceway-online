"""FSM state groups for customer flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SearchFlow(StatesGroup):
    waiting_query = State()


class CheckoutFlow(StatesGroup):
    full_name = State()
    phone = State()
    address = State()
    area = State()
    landmark = State()
    preferred_time = State()
    note = State()
    confirm = State()


class PaymentFlow(StatesGroup):
    waiting_proof = State()


class AskFlow(StatesGroup):
    waiting_question = State()
