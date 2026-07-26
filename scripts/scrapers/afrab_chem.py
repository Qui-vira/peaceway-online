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
        img = tile.css_first("img")
        if img is None:
            continue
        src = base.absolute(url, img.attrib.get("src") or img.attrib.get("data-src"))
        if not src or src in seen:
            continue

        title = ""
        for sel in _TITLE_SELECTORS:
            node = tile.css_first(sel)
            if node is not None and node.text and node.text.strip():
                title = node.text.strip()
                break
        if not title:
            continue
        seen.add(src)

        items.append(
            ScrapedItem(
                manufacturer=MANUFACTURER,
                source_url=url,
                image_url=src,
                title=title,
                # Brand is the tile title as printed. Afrab-Chem does not publish a
                # separate brand field, so we do not invent one.
                brand=re.sub(r"\s+", " ", title).strip(),
                strength=extract_strength(title),
                form=extract_form(title),
                pack_size=extract_pack(title),
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
