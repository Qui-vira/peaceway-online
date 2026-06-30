"""Staff-facing inline keyboards (permission-aware order actions)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.security import has
from app.models import Order, OrderStatus, PaymentMethod, RxStatus


def order_actions(order: Order, role_keys: set[str]) -> InlineKeyboardMarkup:
    """Build the action buttons relevant to this order's state and the staff's permissions."""
    kb = InlineKeyboardBuilder()
    code = order.code

    # Prescription review — pharmacist roles only (safety override in rbac).
    if order.rx_status in (RxStatus.PRESCRIPTION_REQUIRED, RxStatus.PRESCRIPTION_UPLOADED, RxStatus.PHARMACIST_REVIEW):
        if has(role_keys, "approve_prescription"):
            kb.button(text="✅ Approve Rx", callback_data=f"act:rx_approve:{code}")
            kb.button(text="⛔ Reject Rx", callback_data=f"act:rx_reject:{code}")

    is_crypto = order.payment_method == PaymentMethod.CRYPTO

    if order.status == OrderStatus.PAYMENT_SUBMITTED:
        if has(role_keys, "approve_payment"):
            if is_crypto:
                kb.button(text="🔗 Confirm On-chain", callback_data=f"act:crypto_confirm:{code}")
            else:
                kb.button(text="✅ Approve Payment", callback_data=f"act:pay_approve:{code}")
        if has(role_keys, "reject_payment"):
            kb.button(text="❌ Reject Payment", callback_data=f"act:pay_reject:{code}")

    if is_crypto and order.status in (OrderStatus.PAYMENT_APPROVED, OrderStatus.PROCESSING):
        if has(role_keys, "edit_pricing"):  # owner-level (Naira settlement)
            kb.button(text="💵 Mark Naira Settled", callback_data=f"act:crypto_settled:{code}")

    if order.status in (OrderStatus.PAYMENT_APPROVED, OrderStatus.PROCESSING):
        if has(role_keys, "start_packaging"):
            kb.button(text="📦 Start Packaging", callback_data=f"act:packaging:{code}")
        if has(role_keys, "ready_for_dispatch"):
            kb.button(text="🚚 Ready for Dispatch", callback_data=f"act:ready:{code}")

    if order.status in (OrderStatus.PROCESSING, OrderStatus.DISPATCHED):
        if has(role_keys, "assign_rider"):
            kb.button(text="🛵 Assign Rider", callback_data=f"act:assign:{code}")
            kb.button(text="🚀 Book Delivery", callback_data=f"act:book:{code}")
        if has(role_keys, "mark_dispatched"):
            kb.button(text="📨 Mark Dispatched", callback_data=f"act:dispatched:{code}")
        if has(role_keys, "mark_delivered"):
            kb.button(text="🏁 Mark Delivered", callback_data=f"act:delivered:{code}")

    if has(role_keys, "message_customer"):
        kb.button(text="💬 Message Customer", callback_data=f"act:msg:{code}")
    if has(role_keys, "cancel_order") and order.status not in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
        kb.button(text="🚫 Cancel Order", callback_data=f"act:cancel:{code}")

    kb.adjust(2)
    return kb.as_markup()
