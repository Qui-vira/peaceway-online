"""Phase-1 access-control gate DDL — the trigger functions, triggers, and masked
dispatch view that SQLAlchemy models cannot express.

Single source of truth: the Alembic migration imports these statement lists.

Statements are kept SEPARATE (not one ;-joined blob) because the app's async driver
(asyncpg, used by Alembic here) rejects multiple statements per execute. Each list
element is one complete statement; function bodies keep their internal semicolons via
`$fn$` dollar-quoting.

Scope note: this ships TRIGGERS only. Triggers fire for every writer including the
table owner and superuser, so the append-only + Gate-1 + line-binding guarantees hold
today. The complementary REVOKE-from-app-role hardening and clinical-field RLS
(Gate 4) belong to the superuser-removal ticket — RLS cannot bite while the
application connects as a Postgres superuser.
"""
from __future__ import annotations

# GATE 1: no order with a prescription-only line may enter a dispatched /
# out-for-delivery state without a CURRENT approved pharmacist verification.
_FN_GATE1 = r"""
CREATE OR REPLACE FUNCTION enforce_pom_verification_before_dispatch()
RETURNS trigger AS $fn$
DECLARE has_pom boolean; ok boolean;
BEGIN
    IF NOT (
        (NEW.status = 'DISPATCHED' AND OLD.status IS DISTINCT FROM 'DISPATCHED')
        OR (NEW.delivery_status IN ('PICKED_UP','IN_TRANSIT','NEAR_CUSTOMER','DELIVERED')
            AND OLD.delivery_status NOT IN ('PICKED_UP','IN_TRANSIT','NEAR_CUSTOMER','DELIVERED'))
    ) THEN
        RETURN NEW;
    END IF;

    SELECT EXISTS (SELECT 1 FROM order_items oi
                   WHERE oi.order_id = NEW.id AND oi.requires_prescription = true) INTO has_pom;
    IF NOT has_pom THEN
        RETURN NEW;
    END IF;

    -- Latest verification row wins (a later REJECTED/SUPERSEDED overrides an earlier
    -- APPROVED). Verifier must actually hold a pharmacist role, not merely be non-null.
    SELECT (pv.decision = 'APPROVED'
            AND pv.verified_at IS NOT NULL
            AND pv.pharmacist_user_id IS NOT NULL
            AND EXISTS (SELECT 1 FROM admin_role_assignments ara
                        WHERE ara.admin_id = pv.pharmacist_user_id
                          AND ara.role_key IN ('lead_pharmacist','pharmacist_admin')))
    INTO ok
    FROM prescription_verifications pv
    WHERE pv.order_id = NEW.id
    ORDER BY pv.created_at DESC, pv.id DESC
    LIMIT 1;

    IF ok IS NULL OR ok = false THEN
        RAISE EXCEPTION
          'GATE1: order % has a prescription-only item and cannot be dispatched without a current pharmacist verification', NEW.code
          USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$fn$ LANGUAGE plpgsql
"""

# GATES 2 & 3: append-only tables. Fires for the table owner and superuser too.
_FN_DENY = r"""
CREATE OR REPLACE FUNCTION deny_mutation()
RETURNS trigger AS $fn$
BEGIN
    RAISE EXCEPTION
      'APPEND_ONLY: % on % is not allowed; insert a correcting row (amends_record_id) instead', TG_OP, TG_TABLE_NAME
      USING ERRCODE = 'restrict_violation';
END;
$fn$ LANGUAGE plpgsql
"""

# LINE-BINDING: a verification approves the LINES PRESENT at approval. Any line
# change supersedes the current approval (append-only SUPERSEDED row) so Gate 1
# (unchanged) blocks dispatch until a pharmacist re-verifies. Also (re)stamps
# orders.handling_flag, frozen once the order is dispatched.
_FN_LINE = r"""
CREATE OR REPLACE FUNCTION on_order_item_change()
RETURNS trigger AS $fn$
DECLARE
    oid uuid;
    has_pom boolean;
    is_dispatched boolean;
    cur_approved_id uuid;
BEGIN
    oid := COALESCE(NEW.order_id, OLD.order_id);

    IF NOT EXISTS (SELECT 1 FROM orders WHERE id = oid) THEN
        RETURN NULL;
    END IF;

    SELECT (o.status = 'DISPATCHED'
            OR o.delivery_status IN ('PICKED_UP','IN_TRANSIT','NEAR_CUSTOMER','DELIVERED'))
      INTO is_dispatched FROM orders o WHERE o.id = oid;

    SELECT EXISTS (SELECT 1 FROM order_items oi
                   WHERE oi.order_id = oid AND oi.requires_prescription = true)
      INTO has_pom;

    IF NOT is_dispatched THEN
        UPDATE orders
           SET handling_flag = CASE WHEN has_pom THEN 'RX_ID_CHECK' ELSE 'STANDARD' END
         WHERE id = oid;
    END IF;

    SELECT l.id INTO cur_approved_id
      FROM (SELECT id, decision FROM prescription_verifications
             WHERE order_id = oid ORDER BY created_at DESC, id DESC LIMIT 1) l
     WHERE l.decision = 'APPROVED';

    IF cur_approved_id IS NOT NULL THEN
        INSERT INTO prescription_verifications(order_id, decision, amends_record_id, note)
        VALUES (oid, 'SUPERSEDED', cur_approved_id, 'auto: order line changed after verification');
    END IF;

    RETURN NULL;
END;
$fn$ LANGUAGE plpgsql
"""

# GATE 6: masked dispatch view — no product fields, no order_items projection.
_VIEW = r"""
CREATE VIEW dispatch_delivery_masked AS
SELECT
    o.id                       AS order_id,
    o.code                     AS order_code,
    o.delivery_name            AS recipient_name,
    o.delivery_phone           AS phone,
    o.delivery_address         AS address,
    o.delivery_area            AS zone,
    o.delivery_landmark        AS landmark,
    o.delivery_preferred_time  AS delivery_window,
    o.delivery_status          AS delivery_status,
    o.handling_flag            AS handling_flag,
    -- amount_to_collect = order total minus payments already APPROVED, floored at 0.
    --   * orders.total INCLUDES the delivery fee (total = subtotal + delivery_fee +
    --     payment_fee + offramp_fee + handling_fee; app/services/pricing.py).
    --   * refunds do NOT net against the balance: no refund mechanism exists in the
    --     schema today. Revisit this expression when a refund model ships.
    GREATEST(
        o.total - COALESCE((SELECT sum(p.amount) FROM payments p
                            WHERE p.order_id = o.id AND p.status = 'APPROVED'), 0),
        0
    )                          AS amount_to_collect,
    (has_pom.v AND NOT COALESCE(latest.decision = 'APPROVED', false)) AS awaiting_pharmacist_verification
FROM orders o
CROSS JOIN LATERAL (
    SELECT EXISTS (SELECT 1 FROM order_items oi
                   WHERE oi.order_id = o.id AND oi.requires_prescription = true) AS v
) has_pom
LEFT JOIN LATERAL (
    SELECT decision FROM prescription_verifications pv
     WHERE pv.order_id = o.id ORDER BY pv.created_at DESC, pv.id DESC LIMIT 1
) latest ON true
"""

# ── Additive, behavior-safe statements — SHIPPED with the Phase-1 migration ──
# Append-only triggers guard only the new/empty tables + audit_logs (already
# insert-only in the app); on_order_item_change only stamps handling_flag and
# supersedes an existing approval (of which there are none pre-cutover). None of
# these can block live order fulfilment, so they are safe to deploy immediately.
UPGRADE_STATEMENTS: list[str] = [
    _FN_DENY,
    "CREATE TRIGGER trg_presc_verif_append_only "
    "BEFORE UPDATE OR DELETE ON prescription_verifications FOR EACH ROW EXECUTE FUNCTION deny_mutation()",
    "CREATE TRIGGER trg_dispensing_append_only "
    "BEFORE UPDATE OR DELETE ON dispensing_records FOR EACH ROW EXECUTE FUNCTION deny_mutation()",
    "CREATE TRIGGER trg_audit_append_only "
    "BEFORE UPDATE OR DELETE ON audit_logs FOR EACH ROW EXECUTE FUNCTION deny_mutation()",
    _FN_LINE,
    "CREATE TRIGGER trg_order_item_change "
    "AFTER INSERT OR UPDATE OR DELETE ON order_items FOR EACH ROW EXECUTE FUNCTION on_order_item_change()",
    _VIEW,
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP VIEW IF EXISTS dispatch_delivery_masked",
    "DROP TRIGGER IF EXISTS trg_order_item_change ON order_items",
    "DROP FUNCTION IF EXISTS on_order_item_change()",
    "DROP TRIGGER IF EXISTS trg_audit_append_only ON audit_logs",
    "DROP TRIGGER IF EXISTS trg_dispensing_append_only ON dispensing_records",
    "DROP TRIGGER IF EXISTS trg_presc_verif_append_only ON prescription_verifications",
    "DROP FUNCTION IF EXISTS deny_mutation()",
]

# ── DEFERRED — Gate 1 dispatch block. NOT in any migration yet.
# Deploying this activates the trigger the instant the release boots, and with no
# prescription_verifications write-path it would REJECT every POM order dispatch.
# It ships in a follow-up migration together with the pharmacist verify write-path
# (rx_approve inserts a verification row) + a backfill for in-flight approved orders.
# The Postgres test fixture applies these so the full design stays proven.
GATE1_UPGRADE_STATEMENTS: list[str] = [
    _FN_GATE1,
    "CREATE TRIGGER trg_pom_verification_before_dispatch "
    "BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION enforce_pom_verification_before_dispatch()",
]

GATE1_DOWNGRADE_STATEMENTS: list[str] = [
    "DROP TRIGGER IF EXISTS trg_pom_verification_before_dispatch ON orders",
    "DROP FUNCTION IF EXISTS enforce_pom_verification_before_dispatch()",
]
