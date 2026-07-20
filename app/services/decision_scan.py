"""Guard: keep phone numbers out of recorded meeting decisions.

A meeting decision is posted to the staff group (open-decisions block), so a phone
number typed into a decision would leak a contact into a shared channel. Before a
decision is recorded we scan the text; on a hit the handler returns a rephrase
prompt instead of saving. We intentionally do NOT attempt name detection (too many
false positives on ordinary staff names) - only phone-shaped digit runs.
"""
from __future__ import annotations

import re

# Nigerian mobile: local 0[789]xxxxxxxxx (11 digits) or intl +234 7/8/9 xxxxxxxxx.
_NG_PHONE = re.compile(r"(?:\+?234|0)[789]\d{9}")
# Any run of 10+ consecutive digits once separators are stripped (catches spaced /
# dashed numbers and long account-style digit strings).
_LONG_DIGITS = re.compile(r"\d{10,}")


def scan_for_contact(text: str) -> bool:
    """True if the text looks like it contains a phone number / long digit run."""
    if not text:
        return False
    if _NG_PHONE.search(text):
        return True
    stripped = re.sub(r"[\s\-().]", "", text)
    return bool(_LONG_DIGITS.search(stripped))
