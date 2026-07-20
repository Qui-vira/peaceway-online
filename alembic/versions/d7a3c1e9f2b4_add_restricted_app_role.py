"""Add the restricted, non-superuser application role (peaceway_app).

Creates a LOGIN role with exactly the runtime privileges the app needs — CRUD on
tables (via ALL + future default privileges), USAGE/SELECT on sequences, SELECT on
the masked view — and REVOKEs UPDATE/DELETE on the append-only tables (defense in
depth atop the triggers). Being a NON-owner, non-superuser, RLS will apply to it.

This migration is ADDITIVE and inert on its own: it does not change how the app
connects. The cutover (set the role's password + point DATABASE_URL at it, with
MIGRATION_DATABASE_URL kept on the privileged role for Alembic) is a separate,
deliberate ops step. The role is created WITHOUT a password here so no secret lives
in git; the password is set out-of-band (ALTER ROLE ... PASSWORD) at cutover.

Revision ID: d7a3c1e9f2b4
Revises: c5e2b8a4f7d1
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op

revision = "d7a3c1e9f2b4"
down_revision = "c5e2b8a4f7d1"
branch_labels = None
depends_on = None

ROLE = "peaceway_app"
APPEND_ONLY = "prescription_verifications, dispensing_records, audit_logs"

UPGRADE = [
    # Idempotent create (roles are cluster-global; no password -> cannot log in yet).
    f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{ROLE}') "
    f"THEN CREATE ROLE {ROLE} LOGIN; END IF; END $$;",
    f"DO $$ BEGIN EXECUTE format('GRANT CONNECT ON DATABASE %I TO {ROLE}', current_database()); END $$;",
    f"GRANT USAGE ON SCHEMA public TO {ROLE}",
    f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}",
    f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROLE}",
    # Future tables/sequences created by the (privileged) migration role auto-grant.
    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROLE}",
    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {ROLE}",
    # Append-only enforcement at the privilege layer (triggers already block everyone).
    f"REVOKE UPDATE, DELETE ON {APPEND_ONLY} FROM {ROLE}",
]

DOWNGRADE = [
    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {ROLE}",
    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM {ROLE}",
    # Revoke grants in THIS database only. The cluster-global LOGIN role is
    # intentionally NOT dropped: it may hold grants in another database, where
    # DROP ROLE would fail. A leftover role with no grants is harmless and is
    # re-granted idempotently on the next upgrade.
    f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{ROLE}') THEN "
    f"EXECUTE 'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {ROLE}'; "
    f"EXECUTE 'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {ROLE}'; "
    f"EXECUTE 'REVOKE ALL ON SCHEMA public FROM {ROLE}'; "
    f"EXECUTE format('REVOKE ALL ON DATABASE %I FROM {ROLE}', current_database()); "
    f"END IF; END $$;",
]


def upgrade() -> None:
    for stmt in UPGRADE:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE:
        op.execute(stmt)
