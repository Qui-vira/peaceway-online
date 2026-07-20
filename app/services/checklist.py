"""Staff checklist service: generate, complete, and report.

``checklist_instances`` is APPEND ONLY (a Postgres trigger blocks UPDATE/DELETE). The
effective state of an item is the LATEST row for its (template, user, due_date); a
completion/skip inserts a new row that ``supersedes`` the prior one. Never mutate a
row - always insert.

Ownership: only the assignee may complete/skip their own item. This is enforced in
two places - the ``complete_item`` guard here (returns None, no write) and the DB
CHECK ``ck_checklist_own_completion`` as the backstop.

Sessions are injected (like ``rbac_service``) so the same functions serve the bot
handlers, the scheduler jobs, and the tests without opening their own connection.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import lagos_now
from app.models import (
    AdminRoleAssignment,
    AdminUser,
    AuditLog,
    ChecklistInstance,
    ChecklistTemplate,
    MeetingDecision,
)


async def templates_due(session: AsyncSession, on: date) -> list[ChecklistTemplate]:
    """Active templates that apply on ``on``: all daily, plus weekly matching weekday."""
    rows = (
        await session.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.active.is_(True))
        )
    ).scalars().all()
    due: list[ChecklistTemplate] = []
    for t in rows:
        if t.cadence == "daily":
            due.append(t)
        elif t.cadence == "weekly" and t.weekday == on.weekday():
            due.append(t)
    return due


async def _assignees_for_role(session: AsyncSession, role_key: str) -> list[AdminUser]:
    """Active admins holding ``role_key`` (env-bootstrap owners have no row, so a
    checklist can only be assigned to a real ``admin_users`` record)."""
    return list(
        (
            await session.execute(
                select(AdminUser)
                .join(AdminRoleAssignment, AdminRoleAssignment.admin_id == AdminUser.id)
                .where(
                    AdminUser.is_active.is_(True),
                    AdminRoleAssignment.role_key == role_key,
                )
            )
        )
        .scalars()
        .unique()
        .all()
    )


async def generate_instances(session: AsyncSession, on: date) -> list[ChecklistInstance]:
    """Insert one ``pending`` row per (due template, active assignee) for ``on``.

    Idempotent: skips any (template, user, due_date) that already has a row, so it is
    safe to re-run (retry, redeploy, manual trigger). Returns only the rows created
    this call, so the morning job DMs each staffer only their fresh items.
    """
    existing = {
        (tid, uid)
        for tid, uid in (
            await session.execute(
                select(ChecklistInstance.template_id, ChecklistInstance.assigned_user_id)
                .where(ChecklistInstance.due_date == on)
            )
        ).all()
    }
    created: list[ChecklistInstance] = []
    for template in await templates_due(session, on):
        for admin in await _assignees_for_role(session, template.role_key):
            if (template.id, admin.id) in existing:
                continue
            row = ChecklistInstance(
                template_id=template.id,
                assigned_user_id=admin.id,
                due_date=on,
                status="pending",
            )
            session.add(row)
            created.append(row)
            existing.add((template.id, admin.id))
    if created:
        await session.flush()
    return created


async def latest_states(
    session: AsyncSession, user_id: UUID, on: date
) -> list[tuple[ChecklistTemplate, ChecklistInstance]]:
    """Effective (latest) instance per template for a user on ``on``, with its template.

    Ordered by template.sort_order then item_text for a stable checklist display.
    """
    rows = (
        await session.execute(
            select(ChecklistInstance, ChecklistTemplate)
            .join(ChecklistTemplate, ChecklistTemplate.id == ChecklistInstance.template_id)
            .where(
                ChecklistInstance.assigned_user_id == user_id,
                ChecklistInstance.due_date == on,
            )
            .order_by(ChecklistInstance.created_at)
        )
    ).all()
    # Keep the last (newest) instance per template.
    latest: dict[UUID, tuple[ChecklistTemplate, ChecklistInstance]] = {}
    for inst, template in rows:
        latest[template.id] = (template, inst)
    return sorted(latest.values(), key=lambda pair: (pair[0].sort_order, pair[0].item_text))


async def _latest_instance(
    session: AsyncSession, instance_id: UUID
) -> ChecklistInstance | None:
    """Resolve the current effective row for the item that ``instance_id`` belongs to.

    ``instance_id`` may point at a superseded row (a stale button); we re-resolve to
    the newest row for the same (template, user, due_date) so we always supersede the
    true head and never fork the history.
    """
    anchor = await session.get(ChecklistInstance, instance_id)
    if anchor is None:
        return None
    rows = (
        await session.execute(
            select(ChecklistInstance)
            .where(
                ChecklistInstance.template_id == anchor.template_id,
                ChecklistInstance.assigned_user_id == anchor.assigned_user_id,
                ChecklistInstance.due_date == anchor.due_date,
            )
            .order_by(ChecklistInstance.created_at)
        )
    ).scalars().all()
    return rows[-1] if rows else None


async def complete_item(
    session: AsyncSession,
    instance_id: UUID,
    actor_admin_id: UUID,
    status: str,
    skip_reason: str | None = None,
) -> ChecklistInstance | None:
    """Append a done/skipped row for an item, own-only, with an audit record.

    Returns the new row, or None if the item is missing or the actor is not the
    assignee (own-only guard; the DB CHECK is the backstop). ``status`` is
    ``"done"`` or ``"skipped"``.
    """
    if status not in ("done", "skipped"):
        raise ValueError("status must be 'done' or 'skipped'")
    head = await _latest_instance(session, instance_id)
    if head is None:
        return None
    if head.assigned_user_id != actor_admin_id:
        return None  # not your item
    new = ChecklistInstance(
        template_id=head.template_id,
        assigned_user_id=head.assigned_user_id,
        due_date=head.due_date,
        status=status,
        completed_at=lagos_now(),
        completed_by=actor_admin_id,
        skip_reason=skip_reason if status == "skipped" else None,
        supersedes_id=head.id,
    )
    session.add(new)
    session.add(
        AuditLog(
            actor_id=actor_admin_id,
            action=f"checklist_{status}",
            entity="checklist_instance",
            entity_id=str(head.template_id),
            detail={"due_date": head.due_date.isoformat(), "skip_reason": skip_reason},
        )
    )
    await session.flush()
    return new


def _effective_rows(instances: list[ChecklistInstance]) -> list[ChecklistInstance]:
    """Collapse an instance list to the latest row per (template, user)."""
    latest: dict[tuple, ChecklistInstance] = {}
    for inst in sorted(instances, key=lambda i: i.created_at):
        latest[(inst.template_id, inst.assigned_user_id)] = inst
    return list(latest.values())


async def aggregate_status(session: AsyncSession, on: date) -> dict:
    """Counts only for the group post - no names, no per-person, no customer data."""
    instances = (
        await session.execute(
            select(ChecklistInstance).where(ChecklistInstance.due_date == on)
        )
    ).scalars().all()
    effective = _effective_rows(instances)
    total = len(effective)
    done = sum(1 for i in effective if i.status == "done")
    outstanding = [i for i in effective if i.status == "pending"]
    people = {i.assigned_user_id for i in outstanding}
    return {
        "done": done,
        "total": total,
        "outstanding_items": len(outstanding),
        "people_with_outstanding": len(people),
    }


async def per_person_status(session: AsyncSession, on: date) -> list[dict]:
    """Per-person breakdown for the owner DM / PA private status. Not for the group."""
    rows = (
        await session.execute(
            select(ChecklistInstance, ChecklistTemplate, AdminUser)
            .join(ChecklistTemplate, ChecklistTemplate.id == ChecklistInstance.template_id)
            .join(AdminUser, AdminUser.id == ChecklistInstance.assigned_user_id)
            .where(ChecklistInstance.due_date == on)
            .order_by(ChecklistInstance.created_at)
        )
    ).all()
    # Latest instance per (template, user); remember template text + user name.
    latest: dict[tuple, tuple[ChecklistInstance, ChecklistTemplate, AdminUser]] = {}
    for inst, template, admin in rows:
        latest[(template.id, admin.id)] = (inst, template, admin)

    people: dict[UUID, dict] = {}
    for inst, template, admin in latest.values():
        p = people.setdefault(
            admin.id,
            {"name": admin.full_name or f"admin:{admin.telegram_id}", "done": 0, "total": 0, "skipped": []},
        )
        p["total"] += 1
        if inst.status == "done":
            p["done"] += 1
        elif inst.status == "skipped":
            p["skipped"].append((template.item_text, inst.skip_reason))
    return sorted(people.values(), key=lambda p: p["name"].lower())


def _days_outstanding(decision: MeetingDecision, on: date) -> int:
    """Age of a decision in days, from its due_date if set else its created date."""
    ref = decision.due_date or decision.created_at.date()
    return max((on - ref).days, 0)


async def open_decisions(session: AsyncSession, on: date) -> list[dict]:
    """Open decisions with owner name + days outstanding, oldest first.

    Feeds the Monday group prep. A decision overdue by 7+ days sorts to the top.
    """
    rows = (
        await session.execute(
            select(MeetingDecision, AdminUser)
            .outerjoin(AdminUser, AdminUser.id == MeetingDecision.owner_user_id)
            .where(MeetingDecision.status == "open")
        )
    ).all()
    out = [
        {
            "text": d.decision_text,
            "owner": (admin.full_name if admin else None),
            "days_outstanding": _days_outstanding(d, on),
        }
        for d, admin in rows
    ]
    return sorted(out, key=lambda x: x["days_outstanding"], reverse=True)


async def overdue_decisions(session: AsyncSession, on: date) -> list[dict]:
    """Open decisions whose due_date has already passed (for the owner summary)."""
    rows = (
        await session.execute(
            select(MeetingDecision, AdminUser)
            .outerjoin(AdminUser, AdminUser.id == MeetingDecision.owner_user_id)
            .where(
                MeetingDecision.status == "open",
                MeetingDecision.due_date.is_not(None),
                MeetingDecision.due_date < on,
            )
        )
    ).all()
    out = [
        {
            "text": d.decision_text,
            "owner": (admin.full_name if admin else None),
            "days_outstanding": _days_outstanding(d, on),
        }
        for d, admin in rows
    ]
    return sorted(out, key=lambda x: x["days_outstanding"], reverse=True)


async def admins_with_pending(session: AsyncSession, on: date) -> list[tuple[UUID, int]]:
    """(admin_id, pending_count) for every admin with ≥1 effective pending item on ``on``.

    Drives the daily nudge - admins at zero outstanding are absent from the list, so
    they are never messaged (silence on completion is intentional).
    """
    instances = (
        await session.execute(
            select(ChecklistInstance).where(ChecklistInstance.due_date == on)
        )
    ).scalars().all()
    counts: dict[UUID, int] = {}
    for inst in _effective_rows(instances):
        if inst.status == "pending":
            counts[inst.assigned_user_id] = counts.get(inst.assigned_user_id, 0) + 1
    return sorted(counts.items(), key=lambda kv: str(kv[0]))


async def nudged_admin_ids(session: AsyncSession, on: date) -> set[UUID]:
    """Admins already nudged for ``on`` (one nudge per person per day, retry-safe).

    Reads the durable ``checklist_nudge_sent`` audit rows and matches on the due_date in
    detail, so a redeploy or retry at the nudge hour never double-nudges.
    """
    rows = (
        await session.execute(
            select(AuditLog).where(AuditLog.action == "checklist_nudge_sent")
        )
    ).scalars().all()
    target = on.isoformat()
    out: set[UUID] = set()
    for r in rows:
        if r.detail and r.detail.get("due_date") == target and r.entity_id:
            out.add(UUID(r.entity_id))
    return out


async def decisions_closed_since(session: AsyncSession, since: datetime) -> list[str]:
    """Decision texts closed at/after ``since`` (for the weekly owner summary)."""
    rows = (
        await session.execute(
            select(MeetingDecision.decision_text)
            .where(
                MeetingDecision.status == "closed",
                MeetingDecision.closed_at.is_not(None),
                MeetingDecision.closed_at >= since,
            )
        )
    ).scalars().all()
    return list(rows)
