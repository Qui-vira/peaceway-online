"""Embassy Pharmaceutical and Chemicals Limited.

Verified 2026-07-26: https://embassypharma.com.ng/products.html returns HTTP 200.
Product name and strength are encoded in the image FILENAME rather than in alt text
or page copy, e.g. /img/drugs/Amcilin-250.png, /img/injections/Apredin.png.

So this scraper reads the filename, and falls back to nearby caption text when the
filename alone carries no strength. Anything unreadable stays None and cannot match.
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from app.services.image_matching import (
    ScrapedItem,
    extract_form,
    extract_pack,
    extract_strength,
)

from . import base

MANUFACTURER = "Embassy Pharmaceutical and Chemicals Limited"
LISTING_URL = "https://embassypharma.com.ng/products.html"


def _from_filename(src: str) -> str:
    """'/img/drugs/Amcilin-250.png' -> 'Amcilin 250'."""
    stem = unquote(urlparse(src).path.rsplit("/", 1)[-1])
    stem = re.sub(r"\.(png|jpe?g|webp|gif)$", "", stem, flags=re.IGNORECASE)
    return re.sub(r"[-_]+", " ", stem).strip()


async def scrape() -> tuple[list[ScrapedItem], list[str]]:
    problems: list[str] = []
    outcome = await base.fetch(LISTING_URL, wait_selector="img")
    if not outcome.ok:
        return [], [f"{LISTING_URL}: {outcome.skipped_reason}"]

    items: list[ScrapedItem] = []
    seen: set[str] = set()

    for img in outcome.page.css("img"):
        src = base.absolute(LISTING_URL, img.attrib.get("src"))
        if not src or src in seen:
            continue
        # Product imagery lives under /img/<section>/; site chrome does not.
        if not re.search(r"/img/(drugs|injections|care|syrups|tablets)/", src, re.IGNORECASE):
            continue
        seen.add(src)

        label = _from_filename(src)
        alt = (img.attrib.get("alt") or "").strip()
        text = f"{label} {alt}".strip()

        strength = extract_strength(text)
        brand = re.sub(re.escape(strength), "", label, flags=re.IGNORECASE).strip() if strength else label

        items.append(
            ScrapedItem(
                manufacturer=MANUFACTURER,
                source_url=LISTING_URL,
                image_url=src,
                title=text or label,
                brand=brand or None,
                strength=strength,
                form=extract_form(text),
                pack_size=extract_pack(text),
            )
        )

    if not items:
        problems.append(f"{LISTING_URL}: page fetched but no product images parsed")
    return items, problems
