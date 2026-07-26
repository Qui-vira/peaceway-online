"""Greenlife Pharmaceutical Limited.

Verified 2026-07-26: https://greenlifepharmaceuticals.com/products/ returns HTTP 200,
images hosted on Cloudinary with alt set to the product name (G-clav, P-alaxin,
Lonart).

Caveat recorded honestly: the listing publishes the brand but not the strength or
dosage form. Since matching requires all three, items from this scraper will mostly
fail to match and land in the unmatched log. That is the correct outcome — it is a
coverage gap in the source, not something to paper over by relaxing the match.
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

MANUFACTURER = "Greenlife Pharmaceutical Limited"
LISTING_URL = "https://greenlifepharmaceuticals.com/products/"


async def scrape() -> tuple[list[ScrapedItem], list[str]]:
    problems: list[str] = []
    outcome = await base.fetch(LISTING_URL, wait_selector="img")
    if not outcome.ok:
        return [], [f"{LISTING_URL}: {outcome.skipped_reason}"]

    items: list[ScrapedItem] = []
    seen: set[str] = set()

    for img in outcome.page.css("img"):
        alt = (img.attrib.get("alt") or "").strip()
        src = base.absolute(LISTING_URL, img.attrib.get("src") or img.attrib.get("data-src"))
        if not alt or not src or src in seen:
            continue
        if re.search(r"logo|icon|banner|placeholder", src, re.IGNORECASE):
            continue
        seen.add(src)

        items.append(
            ScrapedItem(
                manufacturer=MANUFACTURER,
                source_url=LISTING_URL,
                image_url=src,
                title=alt,
                brand=alt,
                strength=extract_strength(alt),
                form=extract_form(alt),
                pack_size=extract_pack(alt),
            )
        )

    if not items:
        problems.append(f"{LISTING_URL}: page fetched but no product images parsed")
    return items, problems
