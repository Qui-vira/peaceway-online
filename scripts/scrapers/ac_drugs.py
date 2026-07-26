"""A.C. Drugs Ltd.

Verified 2026-07-26: https://www.acdrugslimited.com/Product/ViewProduct/1 returns
HTTP 200 with 1080x771 pack photographs.

Hardest of the six: filenames are camera dumps (IMG-20190507-WA0032.jpg) and alt
text is absent, so identity must come from the caption text beside each photo.
Pages are numbered category views rather than one page per product.
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

MANUFACTURER = "A.C. Drugs Ltd"
# Category ids observed on the site's own navigation on 2026-07-26.
PAGE_URLS = tuple(
    f"https://www.acdrugslimited.com/Product/ViewProduct/{n}" for n in (1, 2, 3, 4, 5, 7, 11)
)

_CARD_SELECTORS = (".product-item", ".card", ".col-lg-4", ".portfolio-item")


def _caption_for(card) -> str:
    for sel in ("h3", "h4", "h5", ".card-title", "figcaption", "p"):
        node = base.first(card, sel)
        if node is not None and node.text and node.text.strip():
            return re.sub(r"\s+", " ", node.text).strip()
    return ""


async def scrape() -> tuple[list[ScrapedItem], list[str]]:
    problems: list[str] = []
    items: list[ScrapedItem] = []
    seen: set[str] = set()

    for url in PAGE_URLS:
        outcome = await base.fetch(url, wait_selector="img")
        if not outcome.ok:
            problems.append(f"{url}: {outcome.skipped_reason}")
            continue

        cards = []
        for sel in _CARD_SELECTORS:
            cards = outcome.page.css(sel)
            if cards:
                break
        if not cards:
            problems.append(f"{url}: no product cards matched {_CARD_SELECTORS}")
            continue

        for card in cards:
            img = base.first(card, "img")
            if img is None:
                continue
            src = base.absolute(url, img.attrib.get("src"))
            if not src or src in seen:
                continue
            if "/DRUGS/" not in src.upper():
                continue

            caption = _caption_for(card)
            if not caption:
                # No caption means no identity. Recorded as a problem rather than
                # guessed from the filename, which carries nothing usable.
                problems.append(f"{url}: image {src.rsplit('/', 1)[-1]} has no caption text")
                continue
            seen.add(src)

            items.append(
                ScrapedItem(
                    manufacturer=MANUFACTURER,
                    source_url=url,
                    image_url=src,
                    title=caption,
                    brand=caption,
                    strength=extract_strength(caption),
                    form=extract_form(caption),
                    pack_size=extract_pack(caption),
                )
            )

    return items, problems
