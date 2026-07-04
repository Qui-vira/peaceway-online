"""Role-Based Access Control definitions (single source of truth).

Roles and their permissions are defined here in code, then seeded into the
`roles` / `permissions` / `role_permissions` tables for visibility and audit.
Who holds each role lives in the DB (`admin_users` + `admin_role_assignments`),
managed by the System Owner from Telegram.

SAFETY OVERRIDE: prescription approval (`approve_prescription`) is granted ONLY to
Lead Pharmacist and Pharmacist Admin — never to any other role, including the
System Owner — per the pharmacy safety rule.
"""
from __future__ import annotations

# ── Role keys ────────────────────────────────────────────────────────────────
SYSTEM_OWNER = "system_owner"
LEAD_PHARMACIST = "lead_pharmacist"
PHARMACIST_ADMIN = "pharmacist_admin"
SALES_SUPPORT = "sales_support"
COMMUNITY_MANAGER = "community_manager"
PACKAGING = "packaging"
DISPATCHER = "dispatcher"
FINANCE = "finance"

ROLES: dict[str, str] = {
    SYSTEM_OWNER: "System Owner / Developer Admin",
    LEAD_PHARMACIST: "Lead Pharmacist",
    PHARMACIST_ADMIN: "Pharmacist Admin",
    SALES_SUPPORT: "Sales / Customer Support",
    COMMUNITY_MANAGER: "Community Manager",
    PACKAGING: "Packaging Staff",
    DISPATCHER: "Dispatcher",
    FINANCE: "Finance / Payment Admin",
}

# ── Permission catalog (key -> human description) ────────────────────────────
PERMISSIONS: dict[str, str] = {
    # System owner / technical
    "manage_env": "Manage environment setup",
    "manage_admins": "Create/disable/remove admins and assign roles",
    "view_staff_directory": "View the staff directory (read-only)",
    "manage_db_sync": "Run catalog import / database sync",
    "manage_alert_settings": "Manage alert settings",
    "manage_integrations": "Manage integrations",
    "manage_logistics": "Manage logistics providers",
    "view_all_logs": "View all activity logs",
    "view_technical_errors": "View technical errors",
    "receive_critical_alerts": "Receive critical failure alerts",
    "view_all_orders": "View all orders",
    "view_all_products": "View all products",
    "edit_pricing": "Edit product prices and pricing",
    "edit_product_safety": "Edit sensitive product safety fields",
    "cancel_order": "Cancel any order",
    # Pharmacist
    "approve_prescription": "Approve or reject prescription medicine orders",
    "reply_pharmacist_tickets": "Reply to pharmacist tickets",
    "review_prescriptions": "Review uploaded prescriptions",
    "view_medicine_orders": "View medicine-related orders",
    "view_customer_questions": "View customer medication questions",
    "view_product_requests": "View customer product/supplement requests",
    "escalate_serious_cases": "Escalate serious cases",
    "override_safety": "Override medicine safety decisions",
    "receive_pharmacist_alerts": "Receive pharmacist alerts",
    "request_more_info": "Request more customer information",
    "convert_conversation_to_order": "Convert approved conversations into orders",
    # Customer CRM
    "view_customers": "View customer profiles and messaging CRM",
    # Sales / support
    "view_customer_orders": "View customer orders",
    "help_complete_orders": "Help customers complete orders",
    "answer_availability": "Answer product availability questions",
    "view_payment_status": "View payment status",
    "escalate_to_pharmacist": "Escalate medicine questions to pharmacist",
    "escalate_to_owner": "Escalate technical issues to System Owner",
    "message_customer": "Message customers through the bot",
    "receive_support_alerts": "Receive customer support alerts",
    # Community manager
    "send_announcements": "Send approved announcements",
    "reply_general_messages": "Reply to general customer messages",
    "view_support_tickets": "View customer support tickets",
    "create_followups": "Create follow-up messages",
    "handle_feedback": "Handle customer feedback",
    "escalate_to_sales": "Escalate orders to sales support",
    # Packaging
    "see_paid_orders": "See paid and approved orders",
    "view_packaging_list": "View product list for packaging",
    "start_packaging": "Mark Start Packaging",
    "ready_for_dispatch": "Mark Ready for Dispatch",
    "report_out_of_stock": "Report out-of-stock issue",
    "notify_fulfillment_issue": "Notify admin order can't be fulfilled",
    # Dispatcher
    "view_assigned_deliveries": "View assigned deliveries",
    "view_delivery_address": "View customer delivery address",
    "view_customer_phone_delivery": "View customer phone for delivery",
    "assign_rider": "Assign a rider / logistics provider",
    "mark_dispatched": "Mark dispatched",
    "mark_picked_up": "Mark Picked Up",
    "mark_in_transit": "Mark In Transit",
    "mark_near_customer": "Mark Near Customer",
    "mark_delivered": "Mark Delivered",
    "mark_failed_delivery": "Mark Failed Delivery",
    "add_delivery_notes": "Add delivery notes",
    # Finance
    "review_payment_proof": "Review payment proof",
    "approve_payment": "Approve payment",
    "reject_payment": "Reject payment",
    "view_payment_history": "View payment history",
    "view_order_totals": "View order totals",
    "view_settlement_records": "View settlement records",
    "export_payment_reports": "Export payment reports",
}

WILDCARD = "*"  # System Owner: full access (except the prescription safety override)

# ── Role -> permission sets ──────────────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, set[str]] = {
    SYSTEM_OWNER: {WILDCARD},
    LEAD_PHARMACIST: {
        "approve_prescription", "reply_pharmacist_tickets", "review_prescriptions",
        "view_medicine_orders", "view_customer_questions", "escalate_serious_cases",
        "override_safety", "receive_pharmacist_alerts", "view_product_requests",
        "edit_pricing", "view_all_products", "view_staff_directory",
        "view_customers",
    },
    PHARMACIST_ADMIN: {
        "approve_prescription", "reply_pharmacist_tickets", "review_prescriptions",
        "view_medicine_orders", "request_more_info", "convert_conversation_to_order",
        "receive_pharmacist_alerts", "view_product_requests",
        "view_customers",
    },
    SALES_SUPPORT: {
        "view_customer_orders", "help_complete_orders", "answer_availability",
        "view_payment_status", "escalate_to_pharmacist", "escalate_to_owner",
        "message_customer", "receive_support_alerts", "view_product_requests",
        "view_customers",
        "view_all_products", "edit_pricing",
    },
    COMMUNITY_MANAGER: {
        "send_announcements", "reply_general_messages", "view_support_tickets",
        "create_followups", "handle_feedback", "escalate_to_sales", "escalate_to_pharmacist",
    },
    PACKAGING: {
        "see_paid_orders", "view_packaging_list", "start_packaging", "ready_for_dispatch",
        "report_out_of_stock", "notify_fulfillment_issue",
    },
    DISPATCHER: {
        "view_assigned_deliveries", "view_delivery_address", "view_customer_phone_delivery",
        "assign_rider", "mark_dispatched", "mark_picked_up", "mark_in_transit",
        "mark_near_customer", "mark_delivered", "mark_failed_delivery", "add_delivery_notes",
    },
    FINANCE: {
        "review_payment_proof", "approve_payment", "reject_payment", "view_payment_history",
        "view_order_totals", "view_settlement_records", "export_payment_reports",
    },
}

# Permissions that the wildcard MUST NOT grant (hard safety override).
WILDCARD_EXCLUDES: set[str] = {"approve_prescription"}

# ── Role -> Telegram menu items (label, callback) ────────────────────────────
ROLE_MENUS: dict[str, list[tuple[str, str]]] = {
    SYSTEM_OWNER: [
        ("📊 System Dashboard", "staff:dashboard"),
        ("🧾 Orders", "staff:orders"),
        ("💊 Products", "staff:products"),
        ("👤 Customers", "staff:customers"),
        ("👥 Staff", "staff:admins"),
        ("💵 Payments", "staff:payments"),
        ("💊 Prescription Order Reviews", "staff:rx"),
        ("📥 Pharmacist Inbox", "staff:tickets"),
        ("📄 Prescriptions", "staff:prescriptions"),
        ("📝 Product Requests", "staff:requests"),
        ("🚚 Delivery", "staff:delivery"),
        ("🪵 Logs", "staff:logs"),
        ("⚙️ Settings", "staff:settings"),
    ],
    LEAD_PHARMACIST: [
        ("💊 Prescription Reviews", "staff:rx"),
        ("📥 Pharmacist Inbox", "staff:tickets"),
        ("📄 Prescriptions", "staff:prescriptions"),
        ("🧾 Medicine Orders", "staff:medorders"),
        ("🆙 Escalated Tickets", "staff:escalated"),
        ("📝 Product Requests", "staff:requests"),
        ("💊 Products", "staff:products"),
        ("👥 Staff", "staff:admins"),
    ],
    PHARMACIST_ADMIN: [
        ("💊 Prescription Reviews", "staff:rx"),
        ("📥 Pharmacist Inbox", "staff:tickets"),
        ("📄 Prescriptions", "staff:prescriptions"),
        ("🧾 Medicine Orders", "staff:medorders"),
        ("📝 Product Requests", "staff:requests"),
    ],
    SALES_SUPPORT: [
        ("💬 Customer Messages", "staff:messages"),
        ("🧾 Orders", "staff:orders"),
        ("👤 Customers", "staff:customers"),
        ("💊 Products", "staff:products"),
        ("💵 Payment Status", "staff:paystatus"),
        ("📝 Product Requests", "staff:requests"),
        ("➡️ Escalate to Pharmacist", "staff:esc_pharm"),
        ("➡️ Escalate to Owner", "staff:esc_owner"),
    ],
    COMMUNITY_MANAGER: [
        ("📝 Customer Feedback", "staff:feedback"),
        ("📢 Announcements", "staff:announce"),
        ("🔁 Follow-ups", "staff:followups"),
        ("🎫 Support Tickets", "staff:tickets"),
    ],
    PACKAGING: [
        ("✅ Paid Orders", "staff:paid"),
        ("📦 Start Packaging", "staff:pack"),
        ("🚚 Ready for Dispatch", "staff:readylist"),
        ("⚠️ Stock Issue", "staff:stockissue"),
    ],
    DISPATCHER: [
        ("🛵 Assigned Deliveries", "staff:deliveries"),
        ("📦 Picked Up", "staff:pickedlist"),
        ("🛣 In Transit", "staff:transitlist"),
        ("🏁 Delivered", "staff:deliveredlist"),
        ("⚠️ Failed Delivery", "staff:failedlist"),
    ],
    FINANCE: [
        ("💵 Pending Payments", "staff:payments"),
        ("📜 Payment History", "staff:payhistory"),
        ("📤 Export Reports", "staff:payexport"),
    ],
}


def role_label(role_key: str) -> str:
    return ROLES.get(role_key, role_key)


def has_permission(role_keys: set[str], permission: str) -> bool:
    """True if any of the given roles grants the permission (honouring overrides)."""
    for rk in role_keys:
        perms = ROLE_PERMISSIONS.get(rk, set())
        if permission in perms:
            return True
        if WILDCARD in perms and permission not in WILDCARD_EXCLUDES:
            return True
    return False


def menu_for(role_keys: set[str]) -> list[tuple[str, str]]:
    """Merged, de-duplicated menu for an admin holding one or more roles."""
    seen: set[str] = set()
    items: list[tuple[str, str]] = []
    for rk in role_keys:
        for label, cb in ROLE_MENUS.get(rk, []):
            if cb not in seen:
                seen.add(cb)
                items.append((label, cb))
    return items
