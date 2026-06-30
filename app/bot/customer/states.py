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


class CryptoFlow(StatesGroup):
    waiting_tx_hash = State()


class AskFlow(StatesGroup):
    waiting_question = State()


class PrescriptionFlow(StatesGroup):
    waiting_file = State()


class ProductRequestFlow(StatesGroup):
    product_name = State()
    strength = State()
    form = State()
    quantity = State()
    area = State()
    phone = State()
    email = State()
    urgency = State()
    note = State()


class TrackRequestsFlow(StatesGroup):
    reply = State()


class EmailGateFlow(StatesGroup):
    waiting_email = State()


class ProfileFlow(StatesGroup):
    waiting_email = State()
