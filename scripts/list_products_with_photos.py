"""List every product that has a photo, so it appears in the shop.

Pricing and stock come later. An unpriced product renders "Price on request" and
offers no Add button (see web/components/app/product-card.tsx), so nothing can reach
a cart at ₦0 — that guard must be deployed before this script is run.

Changes go through products_admin.apply_change(), so each one is written to
price_history and admin_activity_logs and can be reversed per product.

    python -m scripts.list_products_with_photos            # dry run
    python -m scripts.list_products_with_photos --commit
    python -m scripts.list_products_with_photos --unlist --commit   # undo
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter

from sqlalchemy import select

from app.core.db import get_session
from app.models import Product
from app.services.products_admin import apply_change

ADMIN_ID = 0
REASON = "bulk-listed: product has a photo; pricing to follow"


async def run(*, commit: bool, unlist: bool) -> int:
    target = not unlist
    async with get_session() as session:
        stmt = select(Product).where(
            Product.image_id.is_not(None), Product.is_listed.is_(unlist)
        ).order_by(Product.name)
        rows = list((await session.execute(stmt)).scalars().all())

        by_mfr = Counter(p.manufacturer or "(none)" for p in rows)
        print(f"products with a photo needing is_listed={target}: {len(rows)}")
        for m, n in by_mfr.most_common():
            print(f"  {n:5}  {m}")

        if commit:
            for p in rows:
                await apply_change(session, p, "available", target, ADMIN_ID, reason=REASON)
            await session.commit()

        total_listed = len(
            (await session.execute(select(Product).where(Product.is_listed.is_(True)))).scalars().all()
        )

    print("\n" + "=" * 66)
    print(f"{'CHANGED' if commit else 'WOULD CHANGE'}: {len(rows)}")
    print(f"total listed products now: {total_listed}")
    print("=" * 66)
    if not commit:
        print("DRY RUN - nothing written. Re-run with --commit.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--unlist", action="store_true", help="Reverse: hide them again.")
    args = ap.parse_args()
    return asyncio.run(run(commit=args.commit, unlist=args.unlist))


if __name__ == "__main__":
    sys.exit(main())
