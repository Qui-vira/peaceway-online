"""Parse a manufacturer's product page out of crawled Markdown.

WHY THIS EXISTS
There are 1,011 manufacturers in the catalogue. Hand-written CSS selectors do not
scale to that — each site differs, and three of the six existing scrapers broke on a
single API change. Apify's website-content-crawler renders any site to Markdown in a
consistent shape, so one parser covers all of them:

    [![](https://.../Loratadine-syr-3D-01-300x300.jpg)](https://.../loratadine-syrup/)

    #### [Loratadine Syrup](https://.../loratadine-syrup/)

    _Syrup_ (NRN: A4-7551): Loratadine 5 mg

    _Pack size_: 60 ml Plastic bottle.

Each image is followed by the text describing it, up to the next image. That block is
everything the matcher needs — and critically the NAFDAC number, which is the only
identifier that reliably survives the naming mismatch between our catalogue and
manufacturers' marketing names.

This module only reads. It produces ScrapedItem values for the existing matcher;
nothing here decides a pairing or touches a product.
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

# ![alt](url) — the link-wrapped form [![](img)](href) matches too, since we only
# need the inner image.
_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)")

# A markdown heading, optionally a link: "#### [Loratadine Syrup](url)"
_HEADING = re.compile(r"^#{1,6}\s+(?:\[(?P<linked>[^\]]+)\]\([^)]*\)|(?P<plain>.+?))\s*$", re.M)

# Site furniture that is never a product photo.
_CHROME = re.compile(r"logo|icon|favicon|banner|placeholder|avatar|sprite|spacer|footer|header",
                     re.IGNORECASE)


def _strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)      # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # links -> label
    text = re.sub(r"[*_`>#]+", " ", text)                  # emphasis / headings
    return re.sub(r"\s+", " ", text).strip()


def parse_blocks(markdown: str) -> list[tuple[str, str, str]]:
    """Split into (image_url, image_alt, following_text) — one per image."""
    hits = list(_IMAGE.finditer(markdown or ""))
    out: list[tuple[str, str, str]] = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(markdown)
        out.append((m.group("url"), m.group("alt") or "", markdown[m.end(): end]))
    return out


def _title_for(block: str, alt: str) -> str:
    """Prefer the heading that follows the image; fall back to alt, then body text."""
    h = _HEADING.search(block)
    if h:
        return (h.group("linked") or h.group("plain") or "").strip()
    if alt.strip():
        return alt.strip()
    return _strip_markdown(block)[:200]


def parse_catalogue_markdown(
    markdown: str, *, manufacturer: str, source_url: str, min_text: int = 0
) -> list[ScrapedItem]:
    """Read every product image and its description out of one crawled page.

    Items with no usable identity are still returned: the pipeline logs unmatched
    scraped items deliberately, because that is the visible coverage gap.
    """
    items: list[ScrapedItem] = []
    seen: set[str] = set()

    for image_url, alt, block in parse_blocks(markdown):
        if not image_url.startswith(("http://", "https://")):
            continue
        if _CHROME.search(image_url) or _CHROME.search(alt):
            continue
        if image_url in seen:
            continue
        seen.add(image_url)

        title = _title_for(block, alt)
        body = _strip_markdown(block)
        if len(body) < min_text and not title:
            continue

        # Search the heading first, then the surrounding text: a strength printed in
        # the product name is more reliable than one mentioned in marketing copy.
        haystack = f"{title} {body}"

        items.append(
            ScrapedItem(
                manufacturer=manufacturer,
                source_url=source_url,
                image_url=image_url,
                title=(title or body)[:500],
                brand=title or None,
                strength=extract_strength(title) or extract_strength(body),
                form=extract_form(title) or extract_form(body),
                pack_size=extract_pack(haystack),
                nafdac=extract_nafdac(haystack),
            )
        )
    return items
