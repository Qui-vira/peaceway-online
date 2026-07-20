"""Activate Gate 1 (POM dispatch block) with a backfill for in-flight approvals.

Ships together with the pharmacist verify write-path (app/services/verification.py,
wired into rx_approve/rx_reject). Order of operations in upgrade():

1. Backfill: for every order that is currently approved-but-not-yet-dispatched and
   has a prescription-only line, insert an APPROVED prescription_verifications row so
   the newly-activated gate does not block legitimately-approved in-flight orders.
   Attributed to an active pharmacist admin (fails loudly if eligible orders exist but
   none can be found, rather than silently blocking dispatch). verified_at is taken
   from the real rx-approval time where recorded, else now().
2. Activate the Gate 1 trigger (app/core/gate_ddl.GATE1_UPGRADE_STATEMENTS).

Revision ID: c5e2b8a4f7d1
Revises: b3f1a2c9d7e4
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op

from app.core.gate_ddl import GATE1_DOWNGRADE_STATEMENTS, GATE1_UPGRADE_STATEMENTS

revision = "c5e2b8a4f7d1"
down_revision = "b3f1a2c9d7e4"
branch_labels = None
depends_on = None

_BACKFILL = """
DO $$
DECLARE
    ph uuid;
    n  int;
BEGIN
    -- an active pharmacist to attribute historical approvals to
    SELECT ara.admin_id INTO ph
      FROM admin_role_assignments ara
      JOIN admin_users au ON au.id = ara.admin_id
     WHERE ara.role_key IN ('lead_pharmacist','pharmacist_admin')
       AND au.is_active
     ORDER BY au.created_at
     LIMIT 1;

    -- in-flight approved POM orders with no current APPROVED verification
    SELECT count(*) INTO n
      FROM orders o
     WHERE o.rx_status = 'APPROVED_FOR_PAYMENT'
       AND o.status NOT IN ('DISPATCHED','DELIVERED','CANCELLED','REJECTED')
       AND EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.id AND oi.requires_prescription = true)
       AND NOT EXISTS (SELECT 1 FROM prescription_verifications pv WHERE pv.order_id = o.id AND pv.decision = 'APPROVED');

    IF n > 0 AND ph IS NULL THEN
        RAISE EXCEPTION 'Gate1 backfill: % in-flight approved POM order(s) but no active pharmacist admin to attribute to; assign a lead_pharmacist/pharmacist_admin first', n;
    END IF;

    IF n > 0 THEN
        INSERT INTO prescription_verifications (order_id, pharmacist_user_id, decision, verified_at, note)
        SELECT o.id, ph, 'APPROVED',
               COALESCE(
                   (SELECT max(h.created_at) FROM order_status_history h
                     WHERE h.order_id = o.id AND h.field = 'rx_status' AND h.to_value = 'APPROVED_FOR_PAYMENT'),
                   now()),
               'backfill: pre-Gate1 approval (rx_status=APPROVED_FOR_PAYMENT)'
          FROM orders o
         WHERE o.rx_status = 'APPROVED_FOR_PAYMENT'
           AND o.status NOT IN ('DISPATCHED','DELIVERED','CANCELLED','REJECTED')
           AND EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.id AND oi.requires_prescription = true)
           AND NOT EXISTS (SELECT 1 FROM prescription_verifications pv WHERE pv.order_id = o.id AND pv.decision = 'APPROVED');
        RAISE NOTICE 'Gate1 backfill: inserted % verification row(s)', n;
    END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(_BACKFILL)
    for stmt in GATE1_UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    # Drop only the trigger/function. Backfilled verification rows are append-only
    # (protected by trg_presc_verif_append_only) and harmless without the gate, so
    # they are intentionally left in place.
    for stmt in GATE1_DOWNGRADE_STATEMENTS:
        op.execute(stmt)
