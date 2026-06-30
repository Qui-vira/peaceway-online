"""Seed the roles/permissions/role_permissions catalog from the code matrix.

Idempotent. Run after migrations on a fresh database (the app also seeds on
startup, but this is handy for setup/CI).

Usage: python scripts/seed_rbac.py
"""
from __future__ import annotations

import asyncio

from app.services.rbac_service import seed_roles_and_permissions


async def run() -> None:
    await seed_roles_and_permissions()
    print("RBAC roles & permissions seeded.")


if __name__ == "__main__":
    asyncio.run(run())
