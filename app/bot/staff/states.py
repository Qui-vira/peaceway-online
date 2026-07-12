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
    search = State()            # capture admin search query (name or Telegram ID)


class ProductAdminFlow(StatesGroup):
    search = State()            # capture product search query
    value = State()             # capture a new field value
    csv_wait = State()          # awaiting a CSV document upload
    csv_confirm = State()       # awaiting confirm to commit a parsed CSV


class InventoryScanFlow(StatesGroup):
    collecting = State()        # receiving product/shelf photos for an AI scan
    edit_value = State()        # capture a corrected field value for a scan item
    match_search = State()      # capture a product search query for re-matching


class PharmacistFlow(StatesGroup):
    reply = State()             # capture reply to a customer question


class RequestAdminFlow(StatesGroup):
    message = State()           # capture message/note body to send to customer
    price = State()             # capture price for "Send Price to Customer" action


class OrderAdminFlow(StatesGroup):
    search = State()            # capture order reference/code search query


class PaymentAdminFlow(StatesGroup):
    message = State()           # capture freetext message to customer about a payment
    clearer = State()           # capture "request clearer proof" note
