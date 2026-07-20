"""Clinical-field RLS (Gate 4).

Enables row-level security on the clinical tables so only a pharmacist (or an active
break-glass grant) can READ them — plus the owning customer for the customer-facing
ask-a-pharmacist channel. Writes stay app-governed (INSERT permissive); UPDATE/DELETE
are gated to the read set so a non-pharmacist can't exfiltrate via UPDATE ... RETURNING.

Keys on the per-request GUCs set by the actor-context plumbing (2a):
app.current_actor (uuid) + app.current_actor_type (admin|customer|system). Unset =>
default-deny. Only bites because the app now connects as the non-superuser peaceway_app
(superuser removal); the postgres migration role bypasses RLS, which is what we want.

`prescription_verifications` is deliberately NOT covered: the Gate 1 trigger reads it
during a non-pharmacist dispatcher's UPDATE, and RLS would make it invisible there.

Revision ID: e9c4a1b7d2f5
Revises: d7a3c1e9f2b4
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op

revision = "e9c4a1b7d2f5"
down_revision = "d7a3c1e9f2b4"
branch_labels = None
depends_on = None

# ── actor helper functions (STABLE; SECURITY INVOKER so they read as peaceway_app) ──
_FUNCS = [
    "CREATE OR REPLACE FUNCTION app_current_actor() RETURNS uuid LANGUAGE sql STABLE AS "
    "$$ SELECT NULLIF(current_setting('app.current_actor', true), '')::uuid $$",
    "CREATE OR REPLACE FUNCTION app_actor_type() RETURNS text LANGUAGE sql STABLE AS "
    "$$ SELECT NULLIF(current_setting('app.current_actor_type', true), '') $$",
    "CREATE OR REPLACE FUNCTION app_is_pharmacist() RETURNS boolean LANGUAGE sql STABLE AS "
    "$$ SELECT app_actor_type() = 'admin' AND EXISTS ("
    "     SELECT 1 FROM admin_role_assignments ara WHERE ara.admin_id = app_current_actor()"
    "       AND ara.role_key IN ('lead_pharmacist','pharmacist_admin')) $$",
    "CREATE OR REPLACE FUNCTION app_has_break_glass(res text) RETURNS boolean LANGUAGE sql STABLE AS "
    "$$ SELECT app_actor_type() = 'admin' AND EXISTS ("
    "     SELECT 1 FROM break_glass_access bg WHERE bg.user_id = app_current_actor()"
    "       AND bg.expires_at > now() AND bg.resource IN ('clinical', res)) $$",
]

# pharmacist-only tables (+ break-glass)
_PHARM_ONLY = ["prescriptions", "dispensing_records"]
# customer-facing channel: pharmacist + break-glass + owning customer
_CHANNEL = ["pharmacist_questions", "pharmacist_messages"]


def _pharm_read(tbl: str) -> str:
    return f"(app_is_pharmacist() OR app_has_break_glass('{tbl}'))"


def _channel_read(tbl: str) -> str:
    if tbl == "pharmacist_questions":
        owner = "(app_actor_type() = 'customer' AND customer_id = app_current_actor())"
    else:  # pharmacist_messages: owner via the linked question
        owner = (
            "EXISTS (SELECT 1 FROM pharmacist_questions pq WHERE pq.id = pharmacist_messages.question_id "
            "AND app_actor_type() = 'customer' AND pq.customer_id = app_current_actor())"
        )
    return f"(app_is_pharmacist() OR app_has_break_glass('{tbl}') OR {owner})"


def _policies(tbl: str, read: str) -> list[str]:
    return [
        f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY",
        f"CREATE POLICY {tbl}_rls_select ON {tbl} FOR SELECT USING ({read})",
        f"CREATE POLICY {tbl}_rls_insert ON {tbl} FOR INSERT WITH CHECK (true)",
        f"CREATE POLICY {tbl}_rls_update ON {tbl} FOR UPDATE USING ({read}) WITH CHECK (true)",
        f"CREATE POLICY {tbl}_rls_delete ON {tbl} FOR DELETE USING (app_is_pharmacist())",
    ]


def upgrade() -> None:
    for stmt in _FUNCS:
        op.execute(stmt)
    for tbl in _PHARM_ONLY:
        for stmt in _policies(tbl, _pharm_read(tbl)):
            op.execute(stmt)
    for tbl in _CHANNEL:
        for stmt in _policies(tbl, _channel_read(tbl)):
            op.execute(stmt)


def downgrade() -> None:
    for tbl in _PHARM_ONLY + _CHANNEL:
        for pol in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY IF EXISTS {tbl}_rls_{pol} ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")
    for fn in ("app_has_break_glass(text)", "app_is_pharmacist()", "app_actor_type()", "app_current_actor()"):
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
