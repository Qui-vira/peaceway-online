"""Fill missing dosage form and strength from the NAFDAC Greenbook.

The Greenbook is Nigeria's official registered-product database and joins to our
catalogue exactly on nafdac_number, which 8,580 of our products carry. It publishes
no product photographs, but it is authoritative for the fields the catalogue is
missing: 1,273 of our products lack a dosage form or a strength and have an NRN.

    python -m scripts.import_greenbook --applicants        # discover + cache
    python -m scripts.import_greenbook                     # dry run
    python -m scripts.import_greenbook --commit

WHAT IT WILL AND WILL NOT DO
Only EMPTY fields are filled. Where our value and the registry's disagree the row is
reported and left alone — our value may reflect the physical pack a pharmacist
checked, and silently overwriting a strength on a medicine record is precisely the
kind of change this codebase refuses to make automatically.

Every write goes through products_admin.apply_change(), so the original lands in
price_history and any row can be put back.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
from sqlalchemy import or_, select

from app.core.db import engine, get_session
from app.models import Product
from app.services.greenbook import merge_records, parse_applicant_page
from app.services.products_admin import apply_change

API = "https://api.firecrawl.dev/v2"
CACHE = Path("scripts/video/out/greenbook")
BASE = "https://greenbook.nafdac.gov.ng"
ADMIN_ID = 0
REASON = "NAFDAC Greenbook (authoritative registry), filled empty field"


def run_async(coro):
    """asyncio.run() a coroutine, then drop the connection pool.

    This script enters the event loop twice — once to read our manufacturers, once
    to apply the records — with an hour of scraping in between. app.core.db.engine
    is a module-level singleton, so without this the second asyncio.run() inherits
    pooled connections belonging to the first, already-closed loop and dies with
    "Event loop is closed" after the crawl has finished.
    """
    async def wrapped():
        try:
            return await coro
        finally:
            await engine.dispose()

    return asyncio.run(wrapped())


def _key() -> str:
    k = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not k:
        print("FIRECRAWL_API_KEY not set. See .env.example.", file=sys.stderr)
        raise SystemExit(2)
    return k


def scrape(client: httpx.Client, url: str, cache_name: str) -> str:
    path = CACHE / cache_name
    if path.exists():
        return path.read_text(encoding="utf-8")
    for attempt in range(3):
        r = client.post(f"{API}/scrape", json={
            "url": url, "formats": ["markdown"],
            "onlyMainContent": False, "waitFor": 5000,
        }, timeout=120)
        if r.status_code == 429:
            time.sleep(20)
            continue
        r.raise_for_status()
        md = (r.json().get("data") or {}).get("markdown", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
        return md
    return ""


_APPLICANT_LINK = re.compile(
    r"\[\*\*(?P<name>[^*]+?)\*\*\s*(?P<count>\d+)\s+Products.*?/applicant/products/(?P<id>\d+)\)",
    re.S,
)


def discover_applicants(client: httpx.Client, max_pages: int = 60) -> dict[str, dict]:
    """Applicant name -> {id, products}. Paginated server-side at 50 per page."""
    out: dict[str, dict] = {}
    for page in range(1, max_pages + 1):
        url = f"{BASE}/applicants" + (f"?page={page}" if page > 1 else "")
        md = scrape(client, url, f"_applicants_p{page}.md")
        found = 0
        for m in _APPLICANT_LINK.finditer(md or ""):
            name = re.sub(r"\s+", " ", m.group("name")).strip().rstrip(".")
            if not name:
                continue
            out[name] = {"id": int(m.group("id")), "products": int(m.group("count"))}
            found += 1
        print(f"  applicants page {page}: {found} (total {len(out)})", flush=True)
        if found == 0:
            break
        time.sleep(0.8)
    return out


def _norm(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    s = re.sub(r"\b(limited|ltd|plc|nigeria|nig|company|industries|international)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


async def our_manufacturers(*, only_gaps: bool = False) -> list[str]:
    """Distinct manufacturer names. With only_gaps, just those holding a fillable row.

    A product is fillable only if it carries an NRN and an empty form or strength, so
    an applicant whose products are all complete costs a scrape and writes nothing.
    Restricting to gap-holders cuts the crawl from ~1,000 pages to ~350 without
    losing a single fill.
    """
    where = [Product.manufacturer.is_not(None)]
    if only_gaps:
        where += [
            Product.nafdac_number.is_not(None),
            or_(
                Product.dosage_form.is_(None), Product.dosage_form == "",
                Product.strength.is_(None), Product.strength == "",
            ),
        ]
    async with get_session() as s:
        rows = (
            await s.execute(select(Product.manufacturer).where(*where).distinct())
        ).scalars().all()
    return [r for r in rows if r]


async def apply_records(records: dict[str, object], *, commit: bool) -> dict:
    filled = Counter()
    conflicts: list[tuple[str, str, str, str]] = []
    touched = 0

    async with get_session() as session:
        products = list(
            (
                await session.execute(select(Product).where(Product.nafdac_number.is_not(None)))
            ).scalars().all()
        )
        by_nrn: dict[str, list[Product]] = {}
        for p in products:
            by_nrn.setdefault((p.nafdac_number or "").strip().upper(), []).append(p)

        for nrn, rec in records.items():
            for p in by_nrn.get(nrn.upper(), []):
                for field, value in (("dosage_form", rec.form), ("strength", rec.strength)):
                    if not value:
                        continue
                    current = (getattr(p, field) or "").strip()
                    if not current:
                        if commit:
                            await apply_change(session, p, field, value, ADMIN_ID, reason=REASON)
                        filled[field] += 1
                        touched += 1
                    elif current.casefold() != str(value).casefold():
                        conflicts.append((p.name, field, current, str(value)))
        if commit:
            await session.commit()

    return {"filled": filled, "conflicts": conflicts, "touched": touched}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--applicants", action="store_true",
                    help="Only discover and cache the applicant list, then stop.")
    ap.add_argument("--limit", type=int, help="Max applicant pages to fetch.")
    ap.add_argument("--only-gaps", action="store_true",
                    help="Fetch only applicants holding a product with an empty field.")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"Authorization": f"Bearer {_key()}"}) as client:
        applicants = discover_applicants(client)
        print(f"applicants listed in the Greenbook: {len(applicants)}")
        if args.applicants:
            (CACHE / "_applicants.json").write_text(json.dumps(applicants, indent=1), encoding="utf-8")
            print(f"saved {len(applicants)} applicants")
            return 0

        ours = {_norm(m): m for m in run_async(our_manufacturers(only_gaps=args.only_gaps))}
        matched = {n: v for n, v in applicants.items() if _norm(n) in ours and v["products"]}
        scope = "with a fillable product" if args.only_gaps else "in our catalogue"
        print(f"of those, {scope} and holding products: {len(matched)}")

        # Biggest first, so a --limit run covers the most catalogue rows.
        ordered = sorted(matched.items(), key=lambda kv: -kv[1]["products"])
        targets = ordered[: args.limit] if args.limit else ordered
        records = {}
        for i, (name, meta) in enumerate(targets, 1):
            aid = meta["id"]
            md = scrape(client, f"{BASE}/applicant/products/{aid}", f"applicant_{aid}.md")
            recs = parse_applicant_page(md)
            for r in recs:
                # One NRN can surface under two applicants; keep only what they agree
                # on, exactly as duplicates within a single page are treated.
                prior = records.get(r.nafdac)
                records[r.nafdac] = merge_records(prior, r) if prior else r
            print(f"  [{i}/{len(targets)}] {name[:44]:46} {len(recs):>4} records", flush=True)
            time.sleep(1.0)

    print(f"\ntotal registry records collected: {len(records)}")
    result = run_async(apply_records(records, commit=args.commit))

    print("\n" + "=" * 68)
    print(f"{'FILLED' if args.commit else 'WOULD FILL'}: {result['touched']}")
    for field, n in result["filled"].most_common():
        print(f"  {n:>5}  {field}")
    print(f"CONFLICTS (left alone): {len(result['conflicts'])}")
    print("=" * 68)
    for name, field, ours_v, theirs in result["conflicts"][:15]:
        print(f"  {name[:34]:36} {field:12} ours={ours_v[:22]!r} registry={theirs[:22]!r}")
    if not args.commit:
        print("\nDRY RUN - nothing written. Re-run with --commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
