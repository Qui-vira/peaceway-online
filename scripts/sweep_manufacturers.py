"""Crawl and stage image candidates for the top N manufacturers, unattended.

Chains scripts/crawl_manufacturer.py and scripts/ingest_crawled_catalogue.py over
the manufacturers with the most products still lacking a photo.

    python -m scripts.sweep_manufacturers --top 20              # dry run
    python -m scripts.sweep_manufacturers --top 20 --commit

Resumable: a manufacturer whose crawl file already exists is not re-crawled, so an
interrupted run picks up where it stopped. Nothing reaches products.image_id —
everything lands in image_candidates for staff review.
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

OUT_DIR = Path("scripts/video/out/crawls")
PY = sys.executable


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


async def top_manufacturers(n: int) -> list[tuple[str, int]]:
    async with get_session() as session:
        rows = (
            await session.execute(
                select(Product.manufacturer, func.count())
                .where(Product.manufacturer.is_not(None), Product.image_id.is_(None))
                .group_by(Product.manufacturer)
                .order_by(func.count().desc())
                .limit(n)
            )
        ).all()
    return [(m, c) for m, c in rows]


def run(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--skip", action="append", default=[],
                    help="Manufacturer to skip (repeatable).")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = asyncio.run(top_manufacturers(args.top))
    results: list[dict] = []

    for i, (mfr, missing) in enumerate(targets, 1):
        if mfr in args.skip:
            print(f"\n[{i}/{len(targets)}] SKIP {mfr}")
            continue

        print(f"\n{'=' * 72}\n[{i}/{len(targets)}] {mfr}  ({missing} products without a photo)\n{'=' * 72}",
              flush=True)
        path = OUT_DIR / f"{slug(mfr)}.json"

        if path.exists():
            print(f"  already crawled -> {path.name}")
        else:
            code, out = run([PY, "-m", "scripts.crawl_manufacturer", mfr,
                             "--pages", str(args.pages)], timeout=900)
            tail = [l for l in out.splitlines() if l.strip()][-3:]
            for l in tail:
                print("   ", l[:110], flush=True)
            if code != 0 or not path.exists():
                results.append({"manufacturer": mfr, "missing": missing,
                                "status": "no site / no pages", "matched": 0})
                continue

        cmd = [PY, "-m", "scripts.ingest_crawled_catalogue", str(path),
               "--manufacturer", mfr, "--allow-brand-form"]
        if args.commit:
            cmd.append("--commit")
        code, out = run(cmd, timeout=600)

        matched = 0
        m = re.search(r"MATCHED:\s*(\d+)", out)
        if m:
            matched = int(m.group(1))
        parsed = re.search(r"images parsed\s*:\s*(\d+)", out)
        print(f"    images parsed: {parsed.group(1) if parsed else '?'}  |  MATCHED: {matched}",
              flush=True)
        results.append({"manufacturer": mfr, "missing": missing,
                        "status": "ok" if code == 0 else "ingest failed",
                        "matched": matched})

    print("\n\n" + "=" * 72)
    print(f"{'MANUFACTURER':46} {'MISSING':>8} {'MATCHED':>8}  STATUS")
    print("=" * 72)
    for r in results:
        print(f"{r['manufacturer'][:44]:46} {r['missing']:>8} {r['matched']:>8}  {r['status']}")
    total = sum(r["matched"] for r in results)
    print("=" * 72)
    print(f"TOTAL {'STAGED' if args.commit else 'WOULD STAGE'}: {total}")
    if not args.commit:
        print("DRY RUN — re-run with --commit to stage.")
    (OUT_DIR / "sweep_summary.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
