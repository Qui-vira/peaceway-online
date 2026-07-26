"""Detect and repair pollution in products.brand_name.

THE PROBLEM
The PharmaOS import left data-review comments inside the brand column:

    Kadcep## (check dosage form
    Bcosam Tablet## (duplicate, different product
    Kattle Care Multivitamin Injection+++ (check strength format

Those notes are not part of any brand. They were someone's QA annotations, and they
break every exact match the image pipeline attempts — of 8,005 products with a
brand, only 6,326 are clean enough to compare on.

WHAT THIS MODULE WILL AND WILL NOT DO
Only one class of damage is repaired automatically: a trailing parenthetical whose
first word belongs to a closed QA vocabulary, together with any punctuation marker
immediately before it. That is removal of a known non-data artifact, not a judgement
about the medicine, and the original value is preserved in price_history so every
change is reversible.

Everything else is reported for a human and never touched:

  * `Chemilife Daily Multivitamin Drops (Orange flavour` - a real variant, truncated.
    We do not know the missing text, so we cannot restore it.
  * `Emcap Extra Tablet` - the dosage form may or may not be part of the brand.
    Deciding is inference about a medicine, which is exactly what we refuse to do.
  * `Huggies Dry Comfort (Mini) Size 2` - complete and correct. Left alone.

The vocabulary below is closed and derived from the actual data. An unrecognised
word means "leave it alone", so a real parenthetical variant is never stripped.
"""
from __future__ import annotations

import re

# Same closed vocabulary the image matcher uses, so "dosage form embedded in brand"
# means the same thing in both places.
from app.services.image_matching import DOSAGE_FORMS

# First word inside a parenthetical that marks it as a data-review note rather than
# product information. Measured against production: check (147), strength (96),
# duplicate (40), incomplete (17), wrong (13), smpc (12), null (7).
#
# Deliberately EXCLUDED, because they introduce real product information:
# medium, extra, non, long, mini, midi, small, large, size, adult, sterile,
# absorbable, for. Adding a word here silently rewrites medicine data — don't,
# without checking the same way this list was built.
QA_NOTE_OPENERS = frozenset({
    "check", "strength", "duplicate", "incomplete", "wrong", "smpc", "null",
    "verify", "confirm", "missing", "todo", "review",
})

# An explicit annotation marker. Where one of these appears, everything from it
# onward is a note regardless of what follows — the marker is the signal, and no
# pharmaceutical brand contains "##" or "**". This catches notes with no bracket at
# all ("Neutroderm Cream**") and notes whose wording is outside the vocabulary below
# ("Jumetidine Caplet## (dosage form, check pack size").
_MARKER = re.compile(r"\s*(?:#{2,}|\*{2,}|\+{3,})")

# For values with NO marker, a bracket alone is not enough — "Huggies Dry Comfort
# (Mini) Size 2" is a real name. There the first word inside the bracket must be in
# the closed QA vocabulary below.
_QA_TAIL = re.compile(r"[^\sA-Za-z0-9]{0,4}\s*\(\s*(?P<opener>[A-Za-z]+)\b")

# Trailing junk left behind once the note is removed.
_TRAILING = " -–—,;:._*#+"

_ISSUE_QA = "qa_annotation"
_ISSUE_UNCLOSED = "unclosed_paren"
_ISSUE_FORM = "form_embedded"


def strip_qa_annotation(brand: str | None) -> tuple[str | None, str | None]:
    """Return (cleaned, removed_note), or (brand, None) when there is nothing to strip.

    Only strips when the parenthetical's first word is in QA_NOTE_OPENERS.
    """
    if not brand:
        return brand, None

    # Rule 1 — an explicit marker is definitive. Everything from it is a note, and
    # anything before it is preserved, including a legitimate bracket:
    #   "Emvit-C Tablet (White)## (pack size)"  ->  "Emvit-C Tablet (White)"
    marker = _MARKER.search(brand)
    cut = marker.start() if marker else None

    # Rule 2 — no marker, so require a known QA word inside the bracket. Scanning
    # every bracket, not just the first: a brand may legitimately contain one and
    # still carry a note after it.
    if cut is None:
        for m in _QA_TAIL.finditer(brand):
            if m.group("opener").lower() in QA_NOTE_OPENERS:
                cut = m.start()
                break
    if cut is None:
        return brand, None

    cleaned = brand[:cut].rstrip(_TRAILING)
    if not cleaned.strip():
        # Stripping would erase the whole value; leave it for a human.
        return brand, None
    return cleaned.strip(), brand[cut:].strip()


def _parens_balanced(s: str) -> bool:
    return s.count("(") == s.count(")")


# A restored tail longer than this is not a truncated bracket, it is extra product
# information living in `name`. Observed max on real data: 26 characters.
MAX_RESTORE_TAIL = 40


def restore_truncated_brand(
    brand: str | None, name: str | None
) -> tuple[str | None, str | None]:
    """Recover a brand that was truncated mid-bracket, using products.name.

    brand_name is a truncated copy of name in this catalogue:

        brand_name  "Coflax Cough Syrup (Adult"
        name        "Coflax Cough Syrup (Adult)"

    Where the brand is an exact prefix of the name, the brand's brackets are
    unbalanced and the name's are not, the missing characters are already on the row.
    Copying them is recovery, not inference.

    Returns (restored, note) or (brand, None) when the rule does not apply.
    """
    if not brand or not name or brand == name:
        return brand, None
    if not name.startswith(brand):
        return brand, None
    if _parens_balanced(brand) or not _parens_balanced(name):
        return brand, None

    # Cut at the bracket that closes the brand's open one, rather than taking the
    # whole name: `name` may carry strength or dosage form after the bracket, and
    # that does not belong in brand_name.
    depth = brand.count("(") - brand.count(")")
    for i in range(len(brand), len(name)):
        ch = name[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                restored = name[: i + 1].strip()
                tail = len(restored) - len(brand)
                if tail > MAX_RESTORE_TAIL:
                    return brand, None
                return restored, f"restored from name (+{tail} chars)"
    return brand, None


def detect_issues(brand: str | None) -> list[str]:
    """Classify what is wrong with a brand value. Empty list means it looks clean."""
    if not brand or not brand.strip():
        return []

    issues: list[str] = []
    cleaned, note = strip_qa_annotation(brand)
    if note:
        issues.append(_ISSUE_QA)

    # Judge the remaining classes on the value AFTER notional cleanup, so a product
    # is not reported twice for the same underlying text.
    rest = cleaned or brand
    if rest.count("(") != rest.count(")"):
        issues.append(_ISSUE_UNCLOSED)

    low = rest.casefold()
    if any(re.search(rf"\b{re.escape(f)}s?\b", low) for f in DOSAGE_FORMS):
        issues.append(_ISSUE_FORM)

    return issues


def is_auto_fixable(brand: str | None) -> bool:
    """True when the ONLY problem is a QA annotation we can remove deterministically."""
    _, note = strip_qa_annotation(brand)
    return note is not None
