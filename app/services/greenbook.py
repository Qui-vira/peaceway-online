"""Parse NAFDAC Greenbook applicant pages.

The Greenbook is Nigeria's official registered-product database: 9,021 products,
each with a registration number, dosage form, strengths and active ingredients.
It publishes no product photographs — verified 2026-07-27, detail pages carry only
the NAFDAC logo — but it is the authoritative source for the fields our catalogue is
missing, and it joins to us exactly on nafdac_number.

Entry format on an applicant page (real example):

    **Afrab Loratadine Syrup** Syrup** Loratadine

    5 mg/5 mL

    NRN: A4-7551

The bold segment is the product name with the dosage form appended, then the active
ingredients, then the strengths, then the registration number. The name often
carries NAFDAC's own review annotations — "Banedif Ointment## (strength format)",
"Stopacid Suspension## (duplicate)". Those come from the registry itself, not from
our import, which is why they appear in our catalogue too.

This module only reads. Deciding what to write is scripts/import_greenbook.py, and
it only ever fills fields that are empty.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.brand_cleanup import strip_qa_annotation
from app.services.image_matching import DOSAGE_FORMS, extract_nafdac

# One entry: a markdown link whose label is the whole record.
_ENTRY = re.compile(r"\[\*\*(?P<label>.+?)\*\*(?P<body>.*?)\]\((?P<url>[^)]*)\)", re.S)

# Trailing dosage form inside the bold label: "Chloraf Suspension## Suspension".
_FORMS_ALT = "|".join(sorted((re.escape(f) for f in DOSAGE_FORMS), key=len, reverse=True))
_TRAILING_FORM = re.compile(rf"\s+(?P<form>{_FORMS_ALT}s?)\s*$", re.IGNORECASE)
# The registry uses forms our closed vocabulary lacks; accept these too, verbatim.
_EXTRA_FORMS = (
    "solution/drops", "suspension/drops", "dispersible tablet", "chewable tablet",
    "effervescent tablet", "prolonged-release tablet", "powder for suspension",
    "ear drops", "eye drops", "soft gel", "liquid", "granules", "ointment",
)
_EXTRA_ALT = "|".join(sorted((re.escape(f) for f in _EXTRA_FORMS), key=len, reverse=True))
_TRAILING_EXTRA = re.compile(rf"\s+(?P<form>{_EXTRA_ALT})\s*$", re.IGNORECASE)


@dataclass
class GreenbookRecord:
    nafdac: str
    name: str                 # as printed, annotations stripped
    form: str | None
    strength: str | None
    ingredients: str | None
    detail_url: str | None


def _split_name_and_form(label: str) -> tuple[str, str | None]:
    """'Chloraf Suspension## Suspension' -> ('Chloraf Suspension##', 'Suspension')."""
    label = re.sub(r"\\+", "", label)
    label = re.sub(r"\s+", " ", label).strip()
    for pattern in (_TRAILING_EXTRA, _TRAILING_FORM):
        m = pattern.search(label)
        if m:
            return label[: m.start()].strip(), m.group("form").strip()
    return label, None


def _same_product(a: str, b: str) -> bool:
    """Do two entry names refer to the same product, ignoring registry noise?"""
    def key(s: str) -> str:
        s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
        return re.sub(r"\s+", " ", s).strip()

    return key(a) == key(b)


def merge_records(first: GreenbookRecord, later: GreenbookRecord) -> GreenbookRecord:
    """Two entries share one NRN. Keep only what they agree on.

    The registry lists a single registration number twice for genuinely different
    packs — A4-7579 is both "Emcap Suspension 125 mg/5 mL" and "Emzor Paracetamol
    Drops 100mg/15ml". Taking whichever came first would write one pack's strength
    onto the other. Disagreement means we do not know, so the field goes empty and
    the importer, which only fills empty fields, leaves the product alone.

    When the two names are different products (04-0268 is both "Folic Acid Tablet"
    and "Bcosam Tablet"), a value present on only one of them says nothing about the
    other, so it is dropped too. Only same-named entries — re-registrations of one
    product — may complete each other.
    """
    strict = not _same_product(first.name, later.name)

    def agreed(a: str | None, b: str | None) -> str | None:
        if a and b:
            return a if a.casefold() == b.casefold() else None
        return None if strict else (a or b)

    return GreenbookRecord(
        nafdac=first.nafdac,
        name=first.name,
        form=agreed(first.form, later.form),
        strength=agreed(first.strength, later.strength),
        ingredients=agreed(first.ingredients, later.ingredients),
        detail_url=first.detail_url,
    )


def parse_applicant_page(markdown: str) -> list[GreenbookRecord]:
    """Every product record on one applicant page, one per registration number."""
    out: list[GreenbookRecord] = []
    at: dict[str, int] = {}

    for m in _ENTRY.finditer(markdown or ""):
        body = re.sub(r"\\+", "\n", m.group("body"))
        nrn = extract_nafdac(body) or extract_nafdac(m.group("label"))
        if not nrn:
            continue

        raw_name, form = _split_name_and_form(m.group("label"))
        # NAFDAC's own review notes are not part of the product name.
        clean_name, _ = strip_qa_annotation(raw_name)

        # Body lines: ingredients first, then strengths, then "NRN: ...".
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        lines = [ln for ln in lines if not re.match(r"^NRN\s*[:#]", ln, re.IGNORECASE)]
        ingredients = lines[0] if lines else None
        strength = lines[1] if len(lines) > 1 else None
        # "NA", "see Composition" and "Pending" are placeholders, not values.
        if strength and strength.strip().lower() in (
            "na", "n/a", "see composition", "pending", "nil", "none"
        ):
            strength = None

        record = GreenbookRecord(
            nafdac=nrn,
            name=(clean_name or raw_name).strip(),
            form=form,
            strength=strength,
            ingredients=ingredients,
            detail_url=m.group("url") or None,
        )
        if nrn in at:
            out[at[nrn]] = merge_records(out[at[nrn]], record)
        else:
            at[nrn] = len(out)
            out.append(record)
    return out
