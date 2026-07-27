"""Create catalogue entries for crawled manufacturer products we do not stock.

The matcher pairs a scraped image with an existing product. Everything it cannot
pair is currently discarded — but most of those are real products from a real
manufacturer that simply are not in our catalogue yet, with a photograph attached.

    python -m scripts.import_unmatched_products crawl.json \
        --manufacturer "Geneith Pharmaceuticals Limited"            # dry run
    python -m scripts.import_unmatched_products crawl.json \
        --manufacturer "Geneith Pharmaceuticals Limited" --commit

Every created product is unlisted, unpriced and flagged requires_review, so it is a
draft record rather than something a customer can buy. The photograph is attached
directly because the product is created FROM the same record the photo came from —
there is no pairing decision to get wrong, unlike a match.

Duplicates are refused three ways: same NAFDAC number, same brand+form+strength for
that manufacturer, or same product name. A duplicate medicine record is worse than a
missing one.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.db import get_session
from app.models import Product
from app.services import file_storage
from app.services.catalogue_markdown import parse_catalogue_markdown
from app.services.image_matching import canonical, match_against_catalogue
from app.services.product_creation import create_from_scraped, find_duplicate

MATCH_BASIS = "created-from-manufacturer-site"


def load_items(path: Path, manufacturer: str):
    raw = json.loads(path.read_text(encoding="utf-8"))
    pages = raw if isinstance(raw, list) else raw.get("items", [])
    items = []
    for page in pages:
        md = page.get("markdown") or page.get("text") or ""
        if md:
            items += parse_catalogue_markdown(
                md, manufacturer=manufacturer, source_url=page.get("url") or str(path)
            )
    return items


async def run(path: Path, manufacturer: str, *, commit: bool, with_images: bool,
              limit: int | None) -> int:
    items = load_items(path, manufacturer)
    print(f"images parsed        : {len(items)}")

    created = skipped = images = 0
    seen_in_run: set[tuple] = set()
    reasons = Counter()
    made: list[str] = []

    async with get_session() as session:
        products = list(
            (
                await session.execute(select(Product).where(Product.manufacturer == manufacturer))
            ).scalars().all()
        )
        print(f"existing catalogue rows: {len(products)}")

        # Only items the matcher could NOT pair are candidates for creation.
        unmatched = [
            i for i in items
            if not match_against_catalogue(i, products, allow_brand_form=True).matched
        ]
        print(f"unmatched by the matcher: {len(unmatched)}")

        async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
            for item in unmatched:
                if limit is not None and created >= limit:
                    break
                if not (item.title or item.brand):
                    reasons["no usable name"] += 1
                    skipped += 1
                    continue

                # Within this run: the same product appears on several category
                # pages with different image URLs. On --commit the DB check catches
                # the second one, but a dry run writes nothing, so without this the
                # preview count is inflated and misleading.
                key = (canonical(item.title), canonical(item.form), canonical(item.strength))
                if key in seen_in_run:
                    reasons["already seen in this crawl"] += 1
                    skipped += 1
                    continue
                seen_in_run.add(key)

                dup = await find_duplicate(session, item)
                if dup:
                    reasons[dup.reason] += 1
                    skipped += 1
                    continue

                if not commit:
                    created += 1
                    made.append(f"{(item.title or '')[:46]:48} "
                                f"form={item.form or '-'} nrn={item.nafdac or '-'}")
                    continue

                product = await create_from_scraped(session, item)

                if with_images and item.image_url:
                    try:
                        resp = await client.get(item.image_url)
                        if resp.status_code == 200:
                            asset = await file_storage.store_image(
                                session, resp.content,
                                source_url=item.image_url, match_basis=MATCH_BASIS,
                            )
                            product.image_id = asset.id
                            images += 1
                    except Exception:
                        pass  # a product without its photo is still worth having

                created += 1
                made.append(f"{product.name[:46]:48} form={product.dosage_form or '-'}")

        if commit:
            await session.commit()

    print("\n" + "=" * 70)
    print(f"{'CREATED' if commit else 'WOULD CREATE'}: {created}   SKIPPED: {skipped}")
    if commit:
        print(f"IMAGES ATTACHED: {images}")
    print("=" * 70)
    if reasons:
        print("\nWhy items were skipped:")
        for r, n in reasons.most_common():
            print(f"  {n:5}  {r}")
    if made:
        print("\nSample:")
        for line in made[:15]:
            print(f"  {line}")
    print("\nEvery created row: is_listed=False, no price, requires_review=True.")
    if not commit:
        print("DRY RUN - nothing written. Re-run with --commit.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path)
    ap.add_argument("--manufacturer", required=True)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    return asyncio.run(run(args.path, args.manufacturer, commit=args.commit,
                           with_images=not args.no_images, limit=args.limit))


if __name__ == "__main__":
    sys.exit(main())
