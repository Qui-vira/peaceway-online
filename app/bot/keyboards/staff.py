"""Staff-facing inline keyboards (role-aware order actions)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.security import can
from app.models import Order, OrderStatus, RxStatus
from app.models.ops import StaffRole


def order_actions(order: Order, role: StaffRole | None) -> InlineKeyboardMarkup:
    """Build the action buttons relevant to this order's state and the staff role."""
    kb = InlineKeyboardBuilder()
    code = order.code

    # Prescription review (pharmacist/owner) when relevant.
    if order.rx_status in (RxStatus.PRESCRIPTION_REQUIRED, RxStatus.PRESCRIPTION_UPLOADED, RxStatus.PHARMACIST_REVIEW):
        if can(role, "review_prescription"):
            kb.button(text="✅ Approve Rx", callback_data=f"act:rx_approve:{code}")
            kb.button(text="⛔ Reject Rx", callback_data=f"act:rx_reject:{code}")

    if order.status == OrderStatus.PAYMENT_SUBMITTED:
        if can(role, "approve_payment"):
            kb.button(text="✅ Approve Payment", callback_data=f"act:pay_approve:{code}")
        if can(role, "reject_payment"):
            kb.button(text="❌ Reject Payment", callback_data=f"act:pay_reject:{code}")

    if order.status in (OrderStatus.PAYMENT_APPROVED, OrderStatus.PROCESSING):
        if can(role, "start_packaging"):
            kb.button(text="📦 Start Packaging", callback_data=f"act:packaging:{code}")
        if can(role, "ready_for_dispatch"):
            kb.button(text="🚚 Ready for Dispatch", callback_data=f"act:ready:{code}")

    if order.status in (OrderStatus.PROCESSING, OrderStatus.DISPATCHED):
        if can(role, "assign_rider"):
            kb.button(text="🛵 Assign Rider", callback_data=f"act:assign:{code}")
            kb.button(text="🚀 Book Delivery", callback_data=f"act:book:{code}")
        if can(role, "mark_dispatched"):
            kb.button(text="📨 Mark Dispatched", callback_data=f"act:dispatched:{code}")
        if can(role, "mark_delivered"):
            kb.button(text="🏁 Mark Delivered", callback_data=f"act:delivered:{code}")

    if can(role, "message_customer"):
        kb.button(text="💬 Message Customer", callback_data=f"act:msg:{code}")
    if can(role, "cancel_order") and order.status not in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
        kb.button(text="🚫 Cancel Order", callback_data=f"act:cancel:{code}")

    kb.adjust(2)
    return kb.as_markup()
