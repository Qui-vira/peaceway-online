"""Weekly orientation topic rotation.

One topic per week on a fixed twelve-week cycle (owner's marketing plan §10.5). The
week's topic is COMPUTED from the calendar position, never entered by hand, so the
rotation can't drift. Deactivating a topic must not silently drop it: the compute
walks forward to the next active topic and returns the topics it skipped so the caller
can write an audit row for each - a skip is always recorded.

The PA fills the worked example for the week (set_example); only the System Owner may
swap the computed topic (swap_topic), and every swap is audited with a reason.
"""
from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Meeting, OrientationTopic

# The one place to change which calendar week shows topic #1 (sort_order 0). This
# Monday is week 0 of the rotation. Adjust to re-align the start week.
ANCHOR_MONDAY = date(2026, 7, 27)


def monday_of(on: date) -> date:
    """The Monday of the ISO week containing ``on``."""
    return on - timedelta(days=on.weekday())


def week_index(on: date) -> int:
    """Rotation week number for ``on`` (0-based, can be negative before the anchor)."""
    return (monday_of(on) - ANCHOR_MONDAY).days // 7


async def _ordered_topics(session: AsyncSession) -> list[OrientationTopic]:
    return list(
        (
            await session.execute(select(OrientationTopic).order_by(OrientationTopic.sort_order))
        ).scalars().all()
    )


async def computed_topic(
    session: AsyncSession, on: date
) -> tuple[OrientationTopic | None, list[OrientationTopic]]:
    """The week's active topic + any inactive topics skipped to reach it.

    Position is ``week_index(on) % N`` over ALL topics (so positions stay stable as
    topics activate/deactivate); we then walk forward circularly to the first ACTIVE
    topic. Returns (chosen_or_None, skipped_inactive). The caller must audit each skip.
    """
    topics = await _ordered_topics(session)
    if not topics:
        return None, []
    n = len(topics)
    start = week_index(on) % n
    skipped: list[OrientationTopic] = []
    for step in range(n):
        t = topics[(start + step) % n]
        if t.active:
            return t, skipped
        skipped.append(t)
    return None, skipped  # every topic inactive


async def log_topic_skips(
    session: AsyncSession, on: date, skipped: list[OrientationTopic]
) -> None:
    """Write one audit row per inactive topic skipped by the rotation - never silent."""
    for t in skipped:
        session.add(
            AuditLog(
                action="orientation_topic_skipped",
                entity="orientation_topic",
                entity_id=str(t.id),
                detail={"week_of": monday_of(on).isoformat(), "sort_order": t.sort_order},
            )
        )


async def ensure_week_meeting(
    session: AsyncSession, monday: date, topic_id: UUID | None
) -> Meeting:
    """Get-or-create the meeting row for ``monday``, stamping the computed topic."""
    meeting = (
        await session.execute(select(Meeting).where(Meeting.meeting_date == monday))
    ).scalar_one_or_none()
    if meeting is None:
        meeting = Meeting(meeting_date=monday, topic_id=topic_id)
        session.add(meeting)
        await session.flush()
    elif meeting.topic_id is None and topic_id is not None:
        meeting.topic_id = topic_id
        await session.flush()
    return meeting


async def set_example(
    session: AsyncSession, meeting_id: UUID, actor_admin_id: UUID | None, text: str
) -> Meeting | None:
    """Fill the weekly worked example. The PA can set this; she cannot change the topic."""
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None:
        return None
    meeting.example_text = text
    session.add(
        AuditLog(
            actor_id=actor_admin_id,
            action="orientation_example_set",
            entity="meeting",
            entity_id=str(meeting.id),
        )
    )
    await session.flush()
    return meeting


async def swap_topic(
    session: AsyncSession,
    meeting_id: UUID,
    new_topic_id: UUID,
    actor_admin_id: UUID | None,
    reason: str,
) -> Meeting | None:
    """System-Owner swap of the computed topic, recording the original + who + why."""
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None:
        return None
    old = meeting.topic_id
    meeting.swapped_from_topic_id = old
    meeting.topic_id = new_topic_id
    meeting.swapped_by = actor_admin_id
    session.add(
        AuditLog(
            actor_id=actor_admin_id,
            action="orientation_topic_swapped",
            entity="meeting",
            entity_id=str(meeting.id),
            reason=reason,
            detail={"from": str(old) if old else None, "to": str(new_topic_id)},
        )
    )
    await session.flush()
    return meeting


async def add_topic(session: AsyncSession, topic_text: str) -> OrientationTopic:
    """Append a new topic at the end of the rotation (System Owner)."""
    topics = await _ordered_topics(session)
    next_order = (topics[-1].sort_order + 1) if topics else 0
    topic = OrientationTopic(sort_order=next_order, topic_text=topic_text, active=True)
    session.add(topic)
    await session.flush()
    return topic


async def set_topic_active(session: AsyncSession, topic_id: UUID, active: bool) -> bool:
    topic = await session.get(OrientationTopic, topic_id)
    if topic is None:
        return False
    topic.active = active
    await session.flush()
    return True
