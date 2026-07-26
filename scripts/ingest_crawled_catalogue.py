"""Turn crawled manufacturer Markdown into staged image candidates.

Pairs with Apify's website-content-crawler: crawl a manufacturer's site, save the
dataset JSON, then run this. One parser covers every site, so a new manufacturer
needs a URL and nothing else — no bespoke selectors, which is what made the
hand-written scrapers brittle.

Writes to image_candidates ONLY. Nothing reaches products.image_id without approval.

    python -m scripts.ingest_crawled_catalogue crawl.json --manufacturer "SKG - Pharma Ltd"
    python -m scripts.ingest_crawled_catalogue crawl.json --manufacturer "..." --commit
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.core.db import get_session
from app.models import ImageCandidate, Product
from app.services.catalogue_markdown import parse_catalogue_markdown
from app.services.image_matching import match_against_catalogue


def load_items(path: Path, manufacturer: str):
    """Apify datasets are a JSON array of {url, markdown, ...}."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    pages = raw if isinstance(raw, list) else raw.get("items", [])
    items = []
    for page in pages:
        md = page.get("markdown") or page.get("text") or ""
        if not md:
            continue
        items += parse_catalogue_markdown(
            md, manufacturer=manufacturer, source_url=page.get("url") or str(path)
        )
    return items, len(pages)


async def run(path: Path, manufacturer: str, *, commit: bool, allow_brand_form: bool) -> int:
    items, pages = load_items(path, manufacturer)
    print(f"pages crawled : {pages}")
    print(f"images parsed : {len(items)}")
    print(f"  with a NAFDAC number: {sum(1 for i in items if i.nafdac)}")

    matched, reasons, staged = 0, Counter(), 0
    async with get_session() as session:
        products = list(
            (
                await session.execute(select(Product).where(Product.manufacturer == manufacturer))
            ).scalars().all()
        )
        print(f"catalogue rows for this manufacturer: {len(products)}")
        if not products:
            print("  NOTHING TO MATCH - check the manufacturer string matches the catalogue exactly")
            return 0

        for item in items:
            result = match_against_catalogue(item, products, allow_brand_form=allow_brand_form)
            if not result.matched:
                reasons[result.reason or "unknown"] += 1
                continue
            matched += 1

            exists = (
                await session.execute(
                    select(ImageCandidate).where(
                        ImageCandidate.image_url == item.image_url,
                        ImageCandidate.product_id == result.product_id,
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue

            if commit:
                session.add(
                    ImageCandidate(
                        product_id=result.product_id,
                        manufacturer=manufacturer,
                        source_url=item.source_url,
                        image_url=item.image_url,
                        scraped_title=item.title[:500],
                        scraped_strength=item.strength,
                        scraped_form=item.form,
                        scraped_pack_size=item.pack_size,
                        match_basis=result.match_basis,
                        status="pending",
                    )
                )
            staged += 1

        if commit:
            await session.commit()

    print("\n" + "=" * 66)
    print(f"MATCHED: {matched}   {'STAGED' if commit else 'WOULD STAGE'}: {staged}")
    print("=" * 66)
    if reasons:
        print("\nWhy images did not match:")
        for r, n in reasons.most_common(6):
            print(f"  {n:5}  {r}")
    if not commit:
        print("\nDRY RUN - nothing written. Re-run with --commit.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="Apify dataset JSON")
    ap.add_argument("--manufacturer", required=True,
                    help="Must match products.manufacturer exactly.")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--allow-brand-form", action="store_true",
                    help="Also pair on brand+form when strength cannot be compared. "
                         "Candidates are flagged and staff must confirm strength.")
    args = ap.parse_args()
    return asyncio.run(run(args.path, args.manufacturer, commit=args.commit,
                           allow_brand_form=args.allow_brand_form))


if __name__ == "__main__":
    sys.exit(main())
