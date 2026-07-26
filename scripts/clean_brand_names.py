"""Strip data-review annotations out of products.brand_name.

Repairs ONE class of damage: a trailing parenthetical whose first word is in a closed
QA vocabulary, plus any punctuation marker before it.

    Bcosam Tablet## (duplicate, different product   ->  Bcosam Tablet
    Kadcep## (check dosage form                     ->  Kadcep

Everything else is reported and left alone — truncated variants cannot be restored
because the missing text is gone, and deciding whether a dosage form belongs in a
brand is inference about a medicine.

Changes go through products_admin.apply_change(), so each one lands in price_history
with its original value and is reversible.

USAGE
    python -m scripts.clean_brand_names            # dry run, writes nothing
    python -m scripts.clean_brand_names --commit
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter

from sqlalchemy import select

from app.core.db import get_session
from app.models import Product
from app.services.brand_cleanup import (
    detect_issues,
    restore_truncated_brand,
    strip_qa_annotation,
)
from app.services.products_admin import apply_change

ADMIN_ID = 0  # scripted cleanup; audit rows record the reason below
REASON_STRIP = "scripted brand_name QA-annotation cleanup"
REASON_RESTORE = "scripted brand_name truncation repair from products.name"


async def run(*, commit: bool, limit: int | None) -> int:
    fixed: list[tuple[str, str, str]] = []
    issues = Counter()
    needs_human: list[tuple[str, list[str]]] = []

    async with get_session() as session:
        products = list(
            (
                await session.execute(
                    select(Product).where(Product.brand_name.is_not(None)).order_by(Product.name)
                )
            ).scalars().all()
        )
        print(f"products with a brand: {len(products)}")

        touched = 0
        for p in products:
            found = detect_issues(p.brand_name)
            for i in found:
                issues[i] += 1
            if not found:
                continue

            original = p.brand_name
            value = original
            reason = None

            # 1. Remove a data-review note, if present.
            stripped, note = strip_qa_annotation(value)
            if note:
                value, reason = stripped, REASON_STRIP

            # 2. Repair a bracket truncated mid-word, using products.name.
            restored, rnote = restore_truncated_brand(value, p.name)
            if rnote:
                value = restored
                reason = REASON_RESTORE if reason is None else f"{REASON_STRIP}; {REASON_RESTORE}"
                issues["truncation_restored"] += 1

            if value != original and (limit is None or touched < limit):
                fixed.append((p.name, original, value))
                if commit:
                    await apply_change(
                        session, p, "brand_name", value, ADMIN_ID, reason=reason
                    )
                touched += 1

            remaining = [
                i for i in detect_issues(value) if i != "qa_annotation"
            ]
            if remaining:
                needs_human.append((value, remaining))

        if commit:
            await session.commit()

    print("\n" + "=" * 72)
    print(f"{'CLEANED' if commit else 'WOULD CLEAN'} : {len(fixed)}")
    print(f"NEEDS A HUMAN         : {len(needs_human)}")
    print("=" * 72)

    auto_fixed = {"qa_annotation", "truncation_restored"}
    print("\nIssue counts across the catalogue:")
    for name, count in issues.most_common():
        tag = " (fixed automatically)" if name in auto_fixed else " (needs a person)"
        print(f"  {count:5}  {name}{tag}")

    print("\nSample of what would change (full values, not truncated):")
    for _name, before, after in fixed[:12]:
        print(f"  BEFORE  {before}")
        print(f"  AFTER   {after}\n")

    print("\nSample left for a human:")
    for brand, reasons in needs_human[:10]:
        print(f"  {brand[:52]:54} {', '.join(reasons)}")

    if not commit:
        print("\nDRY RUN - nothing was written. Re-run with --commit.")
    else:
        print(f"\n{len(fixed)} brands cleaned. Original values are in price_history.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true", help="Write. Without this nothing persists.")
    ap.add_argument("--limit", type=int, help="Only change the first N.")
    args = ap.parse_args()
    return asyncio.run(run(commit=args.commit, limit=args.limit))


if __name__ == "__main__":
    sys.exit(main())
