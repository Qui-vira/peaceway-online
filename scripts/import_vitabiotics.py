"""Import the Vitabiotics catalogue from its public Shopify feed.

This track CREATES products. Vitabiotics appears nowhere among the 1,011
manufacturers already in the catalogue, so there is nothing to match against.

WHY SETTING image_id HERE IS SAFE, UNLIKE TRACK 2
The product and its photograph come from the same record in the manufacturer's own
feed. There is no pairing decision to get wrong, so there is no cross-matching risk
and no staff approval gate. Track 2's scraped images are the opposite case: the
photo and the product come from different sources and must be paired by a human.

HARD RULES (from the brief, enforced below and in tests)
  * is_listed = False on every row, no exception. Nothing reaches the storefront
    until staff price and list it.
  * No prices imported. The feed is GBP; Naira pricing is a staff decision.
  * nafdac_number = None and requires_review = True on every row. A UK site carries
    no NAFDAC registration, and nothing unreviewed may be dispensed.
  * brand_name / dosage_form / pack_size come straight from feed fields. Anything
    that cannot be read directly is left null and reported. Nothing is guessed.

USAGE
    python -m scripts.import_vitabiotics                 # dry run, writes nothing
    python -m scripts.import_vitabiotics --commit
    python -m scripts.import_vitabiotics --limit 5 --commit
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from dataclasses import dataclass, field

from curl_cffi import requests
from sqlalchemy import select

from app.core.db import get_session
from app.models import Product, ProductPricing
from app.services import file_storage

FEED = (
    "https://www.vitabiotics.com/collections/all-vitabiotics-products/"
    "products.json?limit=250&page={page}"
)
MANUFACTURER = "Vitabiotics"
MATCH_BASIS = "vitabiotics-shopify-feed"
DELAY_SECONDS = 3.0
# Plain urllib gets HTTP 429 from this host; the feed only answers browser-like
# clients, so curl_cffi impersonation is required rather than cosmetic.
IMPERSONATE = "chrome"

# product_type values that are not a dosage form. "Bundles" is a multi-product box,
# so it tells us nothing about the form of what is inside.
NON_DOSAGE_TYPES = {"bundles", "bundle", ""}

_SIZE_SUFFIX = re.compile(r"_\d+x\d+(?=\.[a-z]{3,4}$)", re.IGNORECASE)


def full_resolution(src: str) -> str:
    """Strip Shopify's ?v= cache token and any _NNNxNNN size suffix."""
    src = src.split("?", 1)[0]
    return _SIZE_SUFFIX.sub("", src)


@dataclass
class Candidate:
    title: str
    handle: str
    brand: str | None
    form: str | None
    pack_size: str | None
    image_url: str | None
    source_url: str
    nulls: list[str] = field(default_factory=list)


def to_candidate(p: dict) -> Candidate:
    """Read one feed product into our fields. Reads only; never infers."""
    title = (p.get("title") or "").strip()
    handle = (p.get("handle") or "").strip()

    # vendor is the sub-brand ("Ultra", "Feroglobin", "Pregnacare") and is a clean,
    # dedicated field — far safer than parsing it back out of the title.
    brand = (p.get("vendor") or "").strip() or None

    raw_type = (p.get("product_type") or "").strip()
    form = None if raw_type.casefold() in NON_DOSAGE_TYPES else (raw_type or None)

    variants = p.get("variants") or []
    if len(variants) == 1:
        pack_size = (variants[0].get("option1") or "").strip() or None
    else:
        # Multiple pack sizes on one product: there is no single correct answer, so
        # we record none and flag it rather than picking the first.
        pack_size = None

    images = p.get("images") or []
    image_url = full_resolution(images[0]["src"]) if images and images[0].get("src") else None

    c = Candidate(
        title=title,
        handle=handle,
        brand=brand,
        form=form,
        pack_size=pack_size,
        image_url=image_url,
        source_url=f"https://www.vitabiotics.com/products/{handle}" if handle else FEED,
    )
    for name, value in (("brand_name", brand), ("dosage_form", form), ("pack_size", pack_size)):
        if not value:
            c.nulls.append(name)
    if not image_url:
        c.nulls.append("image")
    if len(variants) > 1:
        c.nulls.append(f"pack_size ambiguous ({len(variants)} variants)")
    return c


def fetch_feed(max_pages: int = 10) -> tuple[list[dict], list[str]]:
    """Paginate until the products array is empty. 3 seconds between requests."""
    products: list[dict] = []
    problems: list[str] = []
    page = 1
    while page <= max_pages:
        time.sleep(DELAY_SECONDS)
        try:
            r = requests.get(FEED.format(page=page), impersonate=IMPERSONATE, timeout=45)
        except Exception as exc:
            problems.append(f"page {page}: {exc}")
            break
        if r.status_code != 200:
            problems.append(f"page {page}: HTTP {r.status_code}")
            break
        batch = r.json().get("products", [])
        if not batch:
            break
        products += batch
        page += 1
    return products, problems


def fetch_image(url: str) -> bytes | None:
    time.sleep(DELAY_SECONDS)
    try:
        r = requests.get(url, impersonate=IMPERSONATE, timeout=60)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


async def _existing(session, handle: str, title: str) -> Product | None:
    """Idempotency: same manufacturer + same title means already imported."""
    return (
        await session.execute(
            select(Product).where(
                Product.manufacturer == MANUFACTURER, Product.name == title
            )
        )
    ).scalar_one_or_none()


async def run(*, commit: bool, limit: int | None, with_images: bool) -> int:
    raw, problems = fetch_feed()
    print(f"feed: {len(raw)} products, {len(problems)} problems")
    for p in problems:
        print(f"  PROBLEM {p}")

    candidates = [to_candidate(p) for p in raw]
    if limit:
        candidates = candidates[:limit]

    created = skipped = images_stored = images_failed = 0
    flagged: list[Candidate] = [c for c in candidates if c.nulls]

    async with get_session() as session:
        for c in candidates:
            if await _existing(session, c.handle, c.title) is not None:
                skipped += 1
                continue

            if not commit:
                created += 1
                continue

            product = Product(
                name=c.title,
                # No separate generic name in the feed; the title is the honest value.
                generic_name=c.title,
                brand_name=c.brand,
                dosage_form=c.form,
                pack_size=c.pack_size,
                strength=None,
                manufacturer=MANUFACTURER,
                nafdac_number=None,      # UK site carries no NAFDAC registration
                category="Supplements",  # every product in this feed is a supplement
                requires_prescription=False,
                requires_review=True,    # nothing unreviewed may be dispensed
                is_listed=False,         # never visible until staff price and list it
            )
            session.add(product)
            await session.flush()

            # Pricing row with NO price. The feed is GBP; Naira is a staff decision.
            session.add(ProductPricing(product_id=product.id))

            if with_images and c.image_url:
                data = fetch_image(c.image_url)
                if data:
                    asset = await file_storage.store_image(
                        session, data,
                        source_url=c.image_url,
                        match_basis=MATCH_BASIS,
                    )
                    product.image_id = asset.id
                    images_stored += 1
                else:
                    images_failed += 1
            created += 1

        if commit:
            await session.commit()

    print("\n" + "=" * 72)
    print(f"{'CREATED' if commit else 'WOULD CREATE'}      : {created}")
    print(f"SKIPPED (existing) : {skipped}")
    if commit and with_images:
        print(f"IMAGES STORED      : {images_stored}")
        print(f"IMAGES FAILED      : {images_failed}")
    print(f"FLAGGED (null field): {len(flagged)}")
    print("=" * 72)

    if flagged:
        print("\nProducts with a field we could not read from the feed:")
        for c in flagged:
            print(f"  {c.title[:46]:48} missing: {', '.join(c.nulls)}")

    print("\nEvery imported row: is_listed=False, price=None, nafdac_number=None, "
          "requires_review=True.")
    if not commit:
        print("DRY RUN - nothing was written. Re-run with --commit.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true", help="Write. Without this nothing persists.")
    ap.add_argument("--limit", type=int, help="Only process the first N feed products.")
    ap.add_argument("--no-images", action="store_true", help="Skip image download.")
    args = ap.parse_args()
    return asyncio.run(run(commit=args.commit, limit=args.limit, with_images=not args.no_images))


if __name__ == "__main__":
    sys.exit(main())
