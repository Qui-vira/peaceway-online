"""Emzor Pharmaceutical Industries Limited.

Verified 2026-07-26: https://emzorpharma.com/emzor-products/ returns HTTP 200 with
223 pack photographs on one page.

Emzor is the only verified site that publishes strength AND pack size in the image
alt text, e.g. "Emcap 500mg Caplet 10*10 -image". Brand is whatever remains once
strength, form and pack are removed — extracted conservatively, so anything we
cannot read cleanly becomes None and therefore cannot match.
"""
from __future__ import annotations

import re

from app.services.image_matching import (
    ScrapedItem,
    extract_form,
    extract_pack,
    extract_strength,
)

from . import base

MANUFACTURER = "Emzor Pharmaceutical Industries Limited"
LISTING_URL = "https://emzorpharma.com/emzor-products/"

_TRAILER = re.compile(r"\s*-?\s*image\s*$", re.IGNORECASE)


def _brand_from(alt: str, strength: str | None, form: str | None, pack: str | None) -> str | None:
    """Whatever is left of the alt text once the structured parts are removed."""
    s = _TRAILER.sub("", alt)
    for part in (strength, form, pack):
        if part:
            s = re.sub(re.escape(part), " ", s, flags=re.IGNORECASE)
    # Emzor writes non-breaking spaces between fields.
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip(" -–—·,")
    return s or None


async def scrape() -> tuple[list[ScrapedItem], list[str]]:
    """Return (items, problems). Never raises on a bad page — reports instead."""
    problems: list[str] = []
    outcome = await base.fetch(LISTING_URL, wait_selector="img")
    if not outcome.ok:
        return [], [f"{LISTING_URL}: {outcome.skipped_reason}"]

    items: list[ScrapedItem] = []
    seen: set[str] = set()

    for img in outcome.page.css("img"):
        alt = (img.attrib.get("alt") or "").strip()
        src = base.absolute(LISTING_URL, img.attrib.get("src"))
        if not alt or not src or src in seen:
            continue
        # Site chrome carries no product alt text.
        if re.search(r"logo|icon|banner|placeholder", src, re.IGNORECASE):
            continue
        seen.add(src)

        strength = extract_strength(alt)
        form = extract_form(alt)
        pack = extract_pack(alt)
        brand = _brand_from(alt, strength, form, pack)

        items.append(
            ScrapedItem(
                manufacturer=MANUFACTURER,
                source_url=LISTING_URL,
                image_url=src,
                title=alt,
                brand=brand,
                strength=strength,
                form=form,
                pack_size=pack,
            )
        )

    if not items:
        problems.append(f"{LISTING_URL}: page fetched but no product images parsed")
    return items, problems
