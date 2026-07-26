"""May & Baker Nigeria PLC.

Verified 2026-07-26: https://may-bakerng.com/products/loxagyl returns HTTP 200 with a
3017x2304 pack photograph at /public/images/products/loxagyl-all.jpg, alt "Loxagyl".

One page per product, so this scraper first collects product slugs from the portfolio
index, then visits each — which is why the 3s-per-domain throttle in base.py matters
more here than on single-page sites.
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

MANUFACTURER = "May & Baker Nigeria PLC"
INDEX_URL = "https://may-bakerng.com/products_portfolio"
_PRODUCT_HREF = re.compile(r"/products/[a-z0-9\-]+$", re.IGNORECASE)

# Visiting every product page costs 3s each; cap a single run so it stays bounded.
MAX_PRODUCTS = 60


async def _product_urls(problems: list[str]) -> list[str]:
    outcome = await base.fetch(INDEX_URL, wait_selector="a")
    if not outcome.ok:
        problems.append(f"{INDEX_URL}: {outcome.skipped_reason}")
        return []
    urls: list[str] = []
    for a in outcome.page.css("a"):
        href = base.absolute(INDEX_URL, a.attrib.get("href"))
        if href and _PRODUCT_HREF.search(href) and href not in urls:
            urls.append(href)
    return urls[:MAX_PRODUCTS]


async def scrape() -> tuple[list[ScrapedItem], list[str]]:
    problems: list[str] = []
    items: list[ScrapedItem] = []

    for url in await _product_urls(problems):
        outcome = await base.fetch(url, wait_selector="img")
        if not outcome.ok:
            problems.append(f"{url}: {outcome.skipped_reason}")
            continue

        img = None
        for candidate in outcome.page.css("img"):
            src = candidate.attrib.get("src") or ""
            if "/images/products/" in src:
                img = candidate
                break
        if img is None:
            problems.append(f"{url}: no /images/products/ image on page")
            continue

        src = base.absolute(url, img.attrib.get("src"))
        alt = (img.attrib.get("alt") or "").strip()
        heading = base.first(outcome.page, "h1")
        title = (heading.text.strip() if heading is not None and heading.text else alt) or alt
        body = outcome.page.get_all_text() if hasattr(outcome.page, "get_all_text") else title

        items.append(
            ScrapedItem(
                manufacturer=MANUFACTURER,
                source_url=url,
                image_url=src,
                title=title,
                brand=title or None,
                strength=extract_strength(title) or extract_strength(body),
                form=extract_form(title) or extract_form(body),
                pack_size=extract_pack(title) or extract_pack(body),
            )
        )

    return items, problems
