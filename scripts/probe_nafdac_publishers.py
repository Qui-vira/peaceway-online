"""Find which manufacturers publish NAFDAC registration numbers.

Reconnaissance, not extraction. A full crawl costs ~12 page fetches per
manufacturer; this takes 3, just to answer one question: does this site print an
NRN next to its products?

That question decides everything downstream. Across the first twenty manufacturers,
the two that publish NAFDAC numbers (Me Cure, Afrab-Chem) produced 90 of the 110
candidates ever found; the other eighteen produced 20 between them. Registration
numbers are the only identifier that survives the naming mismatch between our
catalogue and manufacturers' marketing names, so finding more publishers is worth
far more than crawling more sites blindly.

    python -m scripts.probe_nafdac_publishers --start 21 --count 30

Writes nothing to the database. Prints a ranked table and saves probe_results.json
so the full sweep can be pointed at the publishers only.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

from sqlalchemy import func, select

from app.core.db import get_session
from app.models import Product
from app.services.catalogue_markdown import parse_catalogue_markdown

OUT_DIR = Path("scripts/video/out/probes")
PY = sys.executable


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


async def ranked(start: int, count: int) -> list[tuple[str, int]]:
    async with get_session() as session:
        rows = (
            await session.execute(
                select(Product.manufacturer, func.count())
                .where(Product.manufacturer.is_not(None), Product.image_id.is_(None))
                .group_by(Product.manufacturer)
                .order_by(func.count().desc())
                .offset(max(0, start - 1))
                .limit(count)
            )
        ).all()
    return [(m, c) for m, c in rows]


def probe(mfr: str, pages: int) -> dict:
    path = OUT_DIR / f"{slug(mfr)}.json"
    if not path.exists():
        try:
            subprocess.run(
                [PY, "-m", "scripts.crawl_manufacturer", mfr, "--pages", str(pages)],
                capture_output=True, text=True, timeout=420,
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}
        # crawl_manufacturer writes to crawls/; move it under probes/ so a later
        # full crawl is not skipped by the sweep's resume check.
        src = Path("scripts/video/out/crawls") / f"{slug(mfr)}.json"
        if src.exists():
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            src.replace(path)
        else:
            return {"status": "no site"}

    try:
        pages_json = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "unreadable"}

    items = []
    for pg in pages_json:
        items += parse_catalogue_markdown(
            pg.get("markdown", ""), manufacturer=mfr, source_url=pg.get("url", "")
        )
    with_nrn = sum(1 for i in items if i.nafdac)
    return {
        "status": "ok",
        "pages": len(pages_json),
        "images": len(items),
        "nafdac": with_nrn,
        "forms": sum(1 for i in items if i.form),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=int, default=21, help="Rank to start at (1-based).")
    ap.add_argument("--count", type=int, default=30)
    ap.add_argument("--pages", type=int, default=3, help="Pages per probe. Keep small.")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = asyncio.run(ranked(args.start, args.count))
    results = []

    for i, (mfr, missing) in enumerate(targets, args.start):
        r = probe(mfr, args.pages)
        r.update({"manufacturer": mfr, "missing": missing, "rank": i})
        results.append(r)
        flag = "  <-- PUBLISHES NAFDAC" if r.get("nafdac") else ""
        print(f"[{i:>3}] {mfr[:40]:42} missing={missing:>4} "
              f"pages={r.get('pages','-'):>3} images={r.get('images','-'):>4} "
              f"nrn={r.get('nafdac','-'):>4} {r['status']}{flag}", flush=True)

    publishers = [r for r in results if r.get("nafdac")]
    print("\n" + "=" * 74)
    print(f"PROBED {len(results)} manufacturers | NAFDAC publishers found: {len(publishers)}")
    print("=" * 74)
    for r in sorted(publishers, key=lambda r: -r["nafdac"]):
        print(f"  {r['manufacturer'][:44]:46} {r['missing']:>4} products  "
              f"{r['nafdac']:>3}/{r['images']} images carry an NRN")
    if publishers:
        print("\nFull-crawl these with:")
        for r in publishers:
            print(f'  python -m scripts.crawl_manufacturer "{r["manufacturer"]}" --pages 15')

    (OUT_DIR / "probe_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
