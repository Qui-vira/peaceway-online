"""Africa/Lagos time helpers.

Single source for tz-derived dates. Checklist due-dates and completion timestamps
must reflect the pharmacy's local day, never the server's UTC day - a job that runs
at 06:00 Lagos is already 05:00 UTC, and `datetime.now(timezone.utc).date()` would
roll the due_date a day early for anything near midnight. Always route local dates
through here.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

LAGOS = ZoneInfo("Africa/Lagos")


def lagos_now() -> datetime:
    """Current time as a timezone-aware datetime in Africa/Lagos."""
    return datetime.now(LAGOS)


def lagos_today() -> date:
    """Today's local calendar date in Africa/Lagos."""
    return lagos_now().date()
