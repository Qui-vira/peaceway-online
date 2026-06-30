"""Role-based access control models.

`roles`/`permissions`/`role_permissions` are seeded from app.core.rbac (code is the
source of truth). `admin_users` + `admin_role_assignments` hold who has which role
(managed by the System Owner). `admin_activity_logs` records every admin action.
"""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONB, Base, TimestampMixin


class AdminStatus(str, enum.Enum):
    PENDING = "PENDING"    # added by Owner, awaiting explicit activation
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"  # temporary suspension
    REMOVED = "REMOVED"    # soft-removed; roles cleared, audit history kept


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    role_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    permission_key: Mapped[str] = mapped_column(String(60), nullable=False)

    __table_args__ = (UniqueConstraint("role_key", "permission_key", name="uq_role_permission"),)


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    # is_active stays the literal access gate used by every existing query
    # (get_role_keys, recipients_for_roles) — kept in sync with `status` by the
    # service layer so no existing SQL filter needs to change.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[AdminStatus] = mapped_column(
        SAEnum(AdminStatus, name="admin_status"), default=AdminStatus.PENDING, nullable=False
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignments: Mapped[list["AdminRoleAssignment"]] = relationship(
        back_populates="admin", cascade="all, delete-orphan", lazy="selectin"
    )


class AdminRoleAssignment(Base, TimestampMixin):
    __tablename__ = "admin_role_assignments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_id: Mapped[UUID] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    role_key: Mapped[str] = mapped_column(String(40), nullable=False)

    admin: Mapped[AdminUser] = relationship(back_populates="assignments")

    __table_args__ = (UniqueConstraint("admin_id", "role_key", name="uq_admin_role"),)


class AdminActivityLog(Base, TimestampMixin):
    __tablename__ = "admin_activity_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    roles: Mapped[str | None] = mapped_column(String(255))  # comma-separated role keys at action time
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[dict | None] = mapped_column(JSONB)
