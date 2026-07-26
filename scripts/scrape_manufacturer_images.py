"""Scrape manufacturer pack photos and stage them for staff approval.

WHAT THIS WRITES
  image_candidates only. It never touches products.image_id, never touches
  media_assets, and never lists a product. Approval happens in Telegram.

WHAT IT MATCHES ON
  Exact brand AND strength AND dosage form (case-insensitive, whitespace-canonical).
  Pack size is recorded in match_basis for a human to verify, never matched on.
  See app/services/image_matching.py for the full rule and its rationale.

USAGE
    python -m scripts.scrape_manufacturer_images --dry-run
    python -m scripts.scrape_manufacturer_images --manufacturer emzor
    python -m scripts.scrape_manufacturer_images --commit

Dry run is the default. Nothing is written without --commit.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter

from sqlalchemy import select

from app.core.db import get_session
from app.models import ImageCandidate, Product
from app.services.image_matching import ScrapedItem, match_against_catalogue
from scripts.scrapers import SCRAPERS


async def _products_for(session, manufacturer: str) -> list[Product]:
    """Catalogue rows for one manufacturer. Exact manufacturer string, no fuzzing."""
    return list(
        (
            await session.execute(select(Product).where(Product.manufacturer == manufacturer))
        ).scalars().all()
    )


async def _stage(session, item: ScrapedItem, result, *, commit: bool) -> str:
    """Upsert one candidate row. Returns 'new' | 'updated'."""
    existing = (
        await session.execute(
            select(ImageCandidate).where(
                ImageCandidate.image_url == item.image_url,
                ImageCandidate.product_id == result.product_id,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        # Never revive something staff already judged, and never mutate during a
        # dry run — --commit is the only thing that may change the database.
        if commit and existing.status == "pending":
            existing.match_basis = result.match_basis
            existing.scraped_title = item.title[:500]
        return "updated"

    if commit:
        session.add(
            ImageCandidate(
                product_id=result.product_id,
                manufacturer=item.manufacturer,
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
    return "new"


async def run(names: list[str], *, commit: bool, allow_brand_form: bool = False) -> int:
    matched_rows: list[tuple[ScrapedItem, object]] = []
    unmatched_items: list[tuple[ScrapedItem, str]] = []
    all_problems: list[str] = []
    reasons = Counter()

    async with get_session() as session:
        for name in names:
            module = SCRAPERS[name]
            print(f"\n=== {module.MANUFACTURER} ({name}) ===", flush=True)

            items, problems = await module.scrape()
            all_problems.extend(problems)
            print(f"  scraped {len(items)} images, {len(problems)} problems", flush=True)

            products = await _products_for(session, module.MANUFACTURER)
            print(f"  catalogue rows for this manufacturer: {len(products)}", flush=True)

            for item in items:
                result = match_against_catalogue(item, products, allow_brand_form=allow_brand_form)
                if result.matched:
                    matched_rows.append((item, result))
                    await _stage(session, item, result, commit=commit)
                else:
                    unmatched_items.append((item, result.reason or "unknown"))
                    reasons[result.reason or "unknown"] += 1

            # Products this manufacturer makes that got no image at all.
            got = {r.product_id for _, r in matched_rows}
            unmatched_products = [p for p in products if p.id not in got]
            print(f"  matched {len([1 for _, r in matched_rows if r.matched])} "
                  f"| products still without a candidate: {len(unmatched_products)}", flush=True)
            for p in unmatched_products[:10]:
                missing = [
                    f for f in ("brand_name", "strength", "dosage_form")
                    if not (getattr(p, f) or "").strip()
                ]
                note = f"missing {', '.join(missing)}" if missing else "no matching scraped item"
                print(f"      UNMATCHED PRODUCT  {p.name[:52]:54} {note}", flush=True)

        if commit:
            await session.commit()

    print("\n" + "=" * 72)
    print(f"MATCHED (staged as pending) : {len(matched_rows)}")
    print(f"UNMATCHED scraped items     : {len(unmatched_items)}")
    print(f"SCRAPER PROBLEMS            : {len(all_problems)}")
    print("=" * 72)

    if reasons:
        print("\nWhy scraped items did not match:")
        for reason, count in reasons.most_common():
            print(f"  {count:5}  {reason}")

    if unmatched_items:
        print("\nSample unmatched scraped items:")
        for item, reason in unmatched_items[:15]:
            print(f"  - {item.title[:56]:58} {reason[:70]}")

    if all_problems:
        print("\nScraper problems:")
        for p in all_problems[:20]:
            print(f"  - {p[:140]}")

    if not commit:
        print("\nDRY RUN — nothing was written. Re-run with --commit to stage candidates.")
    else:
        print(f"\nStaged {len(matched_rows)} candidates as status=pending.")
        print("Nothing reached products.image_id. Approve in Telegram: Products -> Review Image Candidates.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manufacturer", action="append", choices=sorted(SCRAPERS),
                    help="Run one scraper (repeatable). Default: all.")
    ap.add_argument("--commit", action="store_true",
                    help="Write candidates. Without this nothing is persisted.")
    ap.add_argument("--allow-brand-form", action="store_true",
                    help="Also pair on brand+form when strength cannot be compared. "
                         "Candidates are flagged and staff must confirm strength.")
    args = ap.parse_args()

    names = args.manufacturer or sorted(SCRAPERS)
    return asyncio.run(run(names, commit=args.commit, allow_brand_form=args.allow_brand_form))


if __name__ == "__main__":
    sys.exit(main())
