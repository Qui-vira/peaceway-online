"""Bulk-approve staged image candidates from the command line.

The normal route is Telegram (Products -> Review Image Candidates), where a human
sees each photo and confirms the pack size. This script is the operator equivalent
for when the owner has decided to accept a whole batch.

It uses the SAME service function as the Telegram flow, so nothing is bypassed
downstream: bytes go through file_storage (normalized, EXIF stripped), source_url
and match_basis are written onto the media asset, and every approval is audited.

    python -m scripts.approve_candidates                      # dry run
    python -m scripts.approve_candidates --nafdac-only --commit
    python -m scripts.approve_candidates --commit
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import httpx
from sqlalchemy import select

from app.core.db import get_session
from app.models import ImageCandidate, Product
from app.models.image_candidate import STATUS_PENDING
from app.services import image_candidates as svc

ADMIN_ID = 0  # scripted approval; the audit row records this

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


async def run(*, commit: bool, nafdac_only: bool, limit: int | None) -> int:
    async with get_session() as session:
        stmt = select(ImageCandidate).where(
            ImageCandidate.status == STATUS_PENDING,
            ImageCandidate.product_id.is_not(None),
        )
        if nafdac_only:
            stmt = stmt.where(ImageCandidate.match_basis.like("nafdac=%"))
        pending = list((await session.execute(stmt)).scalars().all())

    if limit:
        pending = pending[:limit]
    print(f"pending candidates to approve: {len(pending)}")

    ok = failed = 0
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        for c in pending:
            try:
                # Some manufacturers serve 403 to a bare client — chemironcare.com
                # returns 403 with no User-Agent and 200 with a browser one. The
                # Referer is the page the image was published on, which is what a
                # browser would send when loading it.
                resp = await client.get(c.image_url, headers={
                    "User-Agent": BROWSER_UA,
                    "Referer": c.source_url or "",
                })
                if resp.status_code != 200:
                    print(f"  SKIP  HTTP {resp.status_code}  {c.scraped_title[:48]}")
                    failed += 1
                    continue
                data = resp.content
            except Exception as exc:
                print(f"  SKIP  {type(exc).__name__}  {c.scraped_title[:48]}")
                failed += 1
                continue

            if not commit:
                print(f"  WOULD APPROVE  {c.scraped_title[:60]}")
                ok += 1
                continue

            async with get_session() as session:
                fresh = await svc.get_candidate(session, c.id)
                try:
                    product = await svc.approve(session, fresh, data, ADMIN_ID)
                    await session.commit()
                    print(f"  APPROVED  {product.name[:52]}")
                    ok += 1
                except Exception as exc:
                    print(f"  FAILED    {c.scraped_title[:44]}: {exc}")
                    failed += 1

    print("\n" + "=" * 66)
    print(f"{'APPROVED' if commit else 'WOULD APPROVE'}: {ok}   FAILED/SKIPPED: {failed}")
    print("=" * 66)
    if not commit:
        print("DRY RUN - nothing published. Re-run with --commit.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--nafdac-only", action="store_true",
                    help="Only candidates matched on NAFDAC number (the strongest identifier).")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    return asyncio.run(run(commit=args.commit, nafdac_only=args.nafdac_only, limit=args.limit))


if __name__ == "__main__":
    sys.exit(main())
