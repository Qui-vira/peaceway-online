"""Message builders for the staff checklist + meeting tracker.

SAFETY: the group-facing builders (``build_group_status``, ``build_monday_prep``)
take ONLY aggregate counts and decision/owner text - never a Customer, Order, or any
per-person checklist. This is structural, not a convention: a customer field cannot
appear in the group because the function is never handed one. ``build_owner_summary``
is the ONLY per-person builder and is sent to the owner's DM, never the group.
"""
from __future__ import annotations

from typing import TypedDict


class Aggregate(TypedDict):
    done: int
    total: int
    outstanding_items: int
    people_with_outstanding: int


class OpenDecision(TypedDict):
    text: str
    owner: str
    days_outstanding: int


def build_group_status(agg: Aggregate) -> str:
    """Aggregate-only status line for the staff group. Counts, no names."""
    if agg["total"] == 0:
        return "🗒 <b>Checklist status</b>\n\nNothing scheduled today."
    lines = [
        "🗒 <b>Checklist status</b>",
        f"✅ Completed {agg['done']} of {agg['total']} items.",
    ]
    if agg["outstanding_items"]:
        lines.append(
            f"⚠️ {agg['outstanding_items']} outstanding across "
            f"{agg['people_with_outstanding']} "
            f"{'person' if agg['people_with_outstanding'] == 1 else 'people'}."
        )
    else:
        lines.append("🎉 Everything is done.")
    return "\n".join(lines)


def build_monday_prep(open_decisions: list[OpenDecision]) -> str:
    """Monday 08:00 group post: open decisions with owner + days outstanding."""
    lines = ["📋 <b>Monday meeting prep</b>", ""]
    if not open_decisions:
        lines.append("No open decisions carried over. 🎉")
        return "\n".join(lines)
    lines.append("<b>Open decisions</b>")
    for d in open_decisions:
        age = d["days_outstanding"]
        flag = " ⏰" if age >= 7 else ""
        owner = d["owner"] or "unassigned"
        lines.append(f"• {d['text']} — {owner} ({age}d){flag}")
    return "\n".join(lines)


def build_owner_summary(
    per_person: list[dict], decisions_closed: list[str], decisions_overdue: list[dict]
) -> str:
    """Monday 18:00 owner DM: per-person completion + skips + decision movement.

    Owner DM ONLY. ``per_person`` items are {name, done, total, skipped:[(item, reason)]}.
    """
    lines = ["📊 <b>Weekly staff summary</b>", ""]
    if per_person:
        lines.append("<b>Completion</b>")
        for p in per_person:
            lines.append(f"• {p['name']}: {p['done']}/{p['total']}")
            for item, reason in p.get("skipped", []):
                lines.append(f"    ⏭ skipped “{item}” — {reason or 'no reason'}")
        lines.append("")
    lines.append(f"<b>Decisions closed this week:</b> {len(decisions_closed)}")
    for text in decisions_closed:
        lines.append(f"    ✅ {text}")
    if decisions_overdue:
        lines.append("")
        lines.append("<b>Overdue decisions</b>")
        for d in decisions_overdue:
            lines.append(f"    ⏰ {d['text']} — {d['owner'] or 'unassigned'} ({d['days_outstanding']}d)")
    return "\n".join(lines)
