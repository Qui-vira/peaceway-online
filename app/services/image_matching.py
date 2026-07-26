"""Exact matching of scraped manufacturer images to catalogue products.

THE SAFETY RULE THIS FILE ENFORCES
A product photo that shows a different pack, strength or manufacturer than what is
dispensed is a patient-safety failure at a NAFDAC-regulated pharmacy. So:

  * Matching is EXACT on brand AND strength AND dosage form. Below an exact match,
    no candidate is produced. There is no fuzzy matching here, no edit distance, no
    embeddings, no category fallback, and none may ever be added.
  * Pack size is NEVER part of the automated decision. It is normalized for display
    and written into match_basis so a human verifies it at approval time.
  * Nothing in this module writes products.image_id.

WHAT "EXACT" MEANS PRECISELY
Comparison is on a canonical form, not the raw string, because the same strength is
written differently by different sites ("500mg" on Emzor, "500 mg" in our catalogue).
The canonical form applies only transformations that cannot change meaning:

    casefold  ->  "500MG" == "500mg"
    collapse internal whitespace runs to one space
    remove the space between a number and its unit  ->  "500 mg" == "500mg"
    unify micro sign and Greek mu  ->  "µg" == "μg"

That is string equality on a normalized form, which is a different thing from fuzzy
matching: "Emcap" never equals "Emcaps", "500mg" never equals "50mg", and
"5 mg/5 mL" never equals "5mg/mL". Every transformation applied is recorded in
match_basis so a reviewer sees exactly what was compared.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# "10 * 10" / "10x10" / "10*10" -> a multiplier pair
_MULTIPLIER = re.compile(r"^(\d+)\s*[*x×]\s*(\d+)$", re.IGNORECASE)
# A number immediately followed by a unit word, possibly space-separated.
_NUM_UNIT = re.compile(r"(\d)\s+([a-zµμ])", re.IGNORECASE)
_WS = re.compile(r"\s+")


def canonical(value: str | None) -> str:
    """Meaning-preserving canonical form used for EXACT comparison.

    Returns "" for None/blank, which never compares equal to anything (see
    `_equal`), so a missing field can't accidentally match another missing field.
    """
    if value is None:
        return ""
    s = _WS.sub(" ", str(value)).strip().casefold()
    s = s.replace("µ", "μ")           # micro sign -> Greek mu
    s = _NUM_UNIT.sub(r"\1\2", s)               # "500 mg" -> "500mg"
    return s


def _equal(a: str | None, b: str | None) -> bool:
    """Exact equality on canonical forms. Blank never matches blank."""
    ca, cb = canonical(a), canonical(b)
    return bool(ca) and ca == cb


@dataclass
class PackNormalization:
    """Display-only normalization of pack notation. Never used to decide a match."""

    raw: str | None
    display: str | None
    notes: list[str] = field(default_factory=list)

    def as_basis(self) -> str:
        if not self.raw:
            return "pack=<none>"
        if self.display != self.raw:
            return f"pack={self.raw}->{self.display}"
        return f"pack={self.raw}"


def normalize_pack(raw: str | None) -> PackNormalization:
    """Tidy pack notation for a human to read. Display only.

    Expands "10*10" to a total unit count, strips spaces around the multiplier,
    lowercases units and treats mL and ml as identical. Every change is recorded in
    `notes` so the reviewer can see what was rewritten.
    """
    if raw is None or not str(raw).strip():
        return PackNormalization(raw=raw, display=None)

    s = _WS.sub(" ", str(raw)).strip()
    notes: list[str] = []

    lowered = s.lower()
    if lowered != s:
        notes.append("lowercased units")
    s = lowered

    m = _MULTIPLIER.match(s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        total = a * b
        notes.append(f"expanded {m.group(1)}*{m.group(2)} to {total} units")
        s = f"{total} units"
    else:
        # Only tighten the spacing; do not compute a total we cannot justify.
        tightened = re.sub(r"\s*([*x×])\s*", r"*", s)
        if tightened != s:
            notes.append("stripped spaces around multiplier")
            s = tightened
        s = _NUM_UNIT.sub(r"\1\2", s)

    return PackNormalization(raw=raw, display=s, notes=notes)


# Dosage forms we will recognise in manufacturer text. Closed vocabulary on purpose:
# an unrecognised word yields None, which blocks the match, rather than a guess.
DOSAGE_FORMS = (
    "soft gel", "dry syrup", "oral solution", "eye drops", "ear drops", "nasal spray",
    "tablet", "caplet", "capsule", "syrup", "suspension", "injection", "infusion",
    "cream", "lotion", "ointment", "gel", "granules", "powder", "solution", "drops",
    "sachet", "suppository", "inhaler", "spray", "emulsion", "elixir",
)

# "500mg", "5 mg/5 mL", "20.5 g", "250 IU" — a number with a unit, optionally a ratio.
_STRENGTH = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|l|iu|%|µg|μg)(?:\s?/\s?\d*(?:\.\d+)?\s?(?:mg|mcg|g|ml|l|iu))?\b",
    re.IGNORECASE,
)
# "10*10", "1*10", "10 x 10", "30's", "30s", "100ml" handled separately by callers.
_PACK = re.compile(r"\b(\d+\s?[*x×]\s?\d+|\d+\s?'?s)\b", re.IGNORECASE)


def extract_strength(text: str | None) -> str | None:
    """First strength-shaped token in the manufacturer's own text, else None.

    Ambiguity resolves to None, never to a guess: no strength means no match.
    """
    if not text:
        return None
    hits = _STRENGTH.findall(text)
    if not hits:
        return None
    m = _STRENGTH.search(text)
    return m.group(0).strip() if m else None


def extract_form(text: str | None) -> str | None:
    """Dosage form, only if it appears verbatim in the closed vocabulary above."""
    if not text:
        return None
    low = text.casefold()
    # Longest first so "soft gel" wins over "gel" and "eye drops" over "drops".
    for form in sorted(DOSAGE_FORMS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(form)}s?\b", low):
            return form
    return None


def extract_pack(text: str | None) -> str | None:
    """Pack notation if present. Display/verification only — never matched on."""
    if not text:
        return None
    m = _PACK.search(text)
    return m.group(0).strip() if m else None


@dataclass
class ScrapedItem:
    """One product as read off a manufacturer's page, before any interpretation."""

    manufacturer: str
    source_url: str
    image_url: str
    title: str
    brand: str | None = None
    strength: str | None = None
    form: str | None = None
    pack_size: str | None = None


@dataclass
class MatchResult:
    matched: bool
    product_id: object | None = None
    match_basis: str | None = None
    reason: str | None = None          # why it failed, for the coverage log


def match_product(item: ScrapedItem, product) -> MatchResult:
    """Exact-match one scraped item against one product.

    Requires brand AND strength AND dosage form to all be present and equal. A
    product missing any of those three cannot match anything — which is precisely
    why Track 1's backfill exists.
    """
    checks = (
        ("brand", item.brand, product.brand_name),
        ("strength", item.strength, product.strength),
        ("form", item.form, product.dosage_form),
    )

    for label, scraped, stored in checks:
        if not canonical(scraped):
            return MatchResult(False, reason=f"scraped item has no {label}")
        if not canonical(stored):
            return MatchResult(False, reason=f"product has no {label} (needs backfill)")
        if not _equal(scraped, stored):
            return MatchResult(
                False,
                reason=f"{label} differs: scraped={scraped!r} product={stored!r}",
            )

    pack = normalize_pack(item.pack_size)
    basis_parts = [
        f"brand={canonical(item.brand)}",
        f"strength={canonical(item.strength)}",
        f"form={canonical(item.form)}",
        pack.as_basis(),
    ]
    basis = "|".join(basis_parts)
    if pack.notes:
        basis += f" [normalized: {'; '.join(pack.notes)}]"
    # Pack size is shown, never decided on — say so in the record itself.
    basis += " [pack not used for matching - verify against the physical pack]"

    return MatchResult(True, product_id=product.id, match_basis=basis)


def match_against_catalogue(item: ScrapedItem, products) -> MatchResult:
    """Match one scraped item against many products.

    An ambiguous result (more than one exact match) is rejected rather than guessed
    at — two products matching the same brand+strength+form means the catalogue has
    duplicates a human needs to resolve.
    """
    hits = [r for r in (match_product(item, p) for p in products) if r.matched]
    if not hits:
        return MatchResult(False, reason="no exact brand+strength+form match")
    if len(hits) > 1:
        return MatchResult(
            False, reason=f"ambiguous: {len(hits)} products share this brand+strength+form"
        )
    return hits[0]
