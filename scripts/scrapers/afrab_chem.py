"""Afrab-Chem Limited.

Verified 2026-07-26: https://www.afrabchem.com/products/ returns HTTP 200 with real
pack photographs, including Loratadine-syr-3D-01.jpg and afrabvite-drops-1.jpg,
both of which correspond to currently-listed Peaceway products.

Unlike Emzor, Afrab-Chem's image alt attributes are EMPTY. Product identity has to
come from the WooCommerce product-tile text next to each image, so this scraper
reads the tile, not the image attributes.
"""
from __future__ import annotations

import re

from app.services.image_matching import (
    ScrapedItem,
    extract_form,
    extract_nafdac,
    extract_pack,
    extract_strength,
)

from . import base

MANUFACTURER = "Afrab-Chem Limited"
LISTING_URL = "https://www.afrabchem.com/products/"

# Category pages carry the same tiles; included so a single run covers the range.
CATEGORY_URLS = (
    "https://www.afrabchem.com/product-category/analgesic/",
    "https://www.afrabchem.com/product-category/anti-allergic/",
    "https://www.afrabchem.com/product-category/antacid/",
    "https://www.afrabchem.com/product-category/anti-bacteria-anti-infective/",
    "https://www.afrabchem.com/product-category/anti-malaria/",
    "https://www.afrabchem.com/product-category/anti-fungal/",
    "https://www.afrabchem.com/product-category/anti-diarhoea/",
    "https://www.afrabchem.com/product-category/anti-spasmodic/",
)

_TILE_SELECTORS = ("li.product", "div.product", "div.wc-block-grid__product")
_TITLE_SELECTORS = ("h2", "h3", ".woocommerce-loop-product__title", "a")


async def _scrape_page(url: str, problems: list[str], seen: set[str]) -> list[ScrapedItem]:
    outcome = await base.fetch(url, wait_selector="img")
    if not outcome.ok:
        problems.append(f"{url}: {outcome.skipped_reason}")
        return []

    tiles = []
    for sel in _TILE_SELECTORS:
        tiles = outcome.page.css(sel)
        if tiles:
            break
    if not tiles:
        problems.append(f"{url}: no product tiles matched {_TILE_SELECTORS}")
        return []

    items: list[ScrapedItem] = []
    for tile in tiles:
        img = base.first(tile, "img")
        if img is None:
            continue
        src = base.absolute(url, img.attrib.get("src") or img.attrib.get("data-src"))
        if not src or src in seen:
            continue

        # The tiles carry NO heading element — h2/h3/.woocommerce-loop-product__title
        # are all absent and the anchor text is empty. The whole product description
        # sits in the tile's own text:
        #   "Loratadine Syrup Syrup (NRN: A4-7551): Loratadine 5 mg Pack size : 60 ml"
        # so read that, and take the NRN from it, which identifies the product exactly.
        title = re.sub(r"\s+", " ", tile.get_all_text() or "").strip()
        if not title:
            for sel in _TITLE_SELECTORS:
                node = base.first(tile, sel)
                if node is not None and node.text and node.text.strip():
                    title = node.text.strip()
                    break
        if not title:
            continue
        seen.add(src)

        # Brand is the text before the NRN parenthetical, which is how the site
        # names the product. Left as-is when there is no NRN to cut at.
        brand = re.split(r"\s*\((?:NRN|NAFDAC)", title, maxsplit=1, flags=re.IGNORECASE)[0]
        brand = re.sub(r"\s+", " ", brand).strip() or None

        items.append(
            ScrapedItem(
                manufacturer=MANUFACTURER,
                source_url=url,
                image_url=src,
                title=title[:500],
                brand=brand,
                strength=extract_strength(title),
                form=extract_form(title),
                pack_size=extract_pack(title),
                # The decisive field: Afrab-Chem prints "(NRN: A4-7551)" on every tile.
                nafdac=extract_nafdac(title),
            )
        )
    return items


async def scrape() -> tuple[list[ScrapedItem], list[str]]:
    problems: list[str] = []
    seen: set[str] = set()
    items: list[ScrapedItem] = []
    for url in (LISTING_URL, *CATEGORY_URLS):
        items.extend(await _scrape_page(url, problems, seen))
    return items, problems
