"""Find a manufacturer's site, crawl its product pages, save the Markdown.

This is the step that could not be automated before: driving Firecrawl from a
script instead of hand-shuttling one crawl at a time through a chat session.
There are 1,011 manufacturers in the catalogue, so the loop has to be unattended.

Pipeline:

    python -m scripts.crawl_manufacturer "SKG - Pharma Ltd"          # find + crawl
    python -m scripts.ingest_crawled_catalogue <out.json> \
        --manufacturer "SKG - Pharma Ltd" --allow-brand-form --commit

Only manufacturer sites are ever crawled — never retailers, aggregators or image
search. The search step is constrained to the company's own domain once found, and
the URL is printed so the operator can see exactly what was read.

Requires FIRECRAWL_API_KEY (see .env.example). scripts/ is excluded from the
deployed container, so this never runs in production.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

API = "https://api.firecrawl.dev/v2"
OUT_DIR = Path("scripts/video/out/crawls")

# Domains that are never a manufacturer's own site. Sourcing from these would break
# the rule that a product photo comes from the company that makes the product.
BLOCKED = re.compile(
    r"(facebook|linkedin|instagram|twitter|x\.com|youtube|wikipedia|zoominfo|"
    r"rocketreach|tracxn|dnb\.com|crunchbase|pinterest|amazon|jumia|konga|"
    r"pharmacompass|indiamart|alibaba|google\.|bing\.)",
    re.IGNORECASE,
)

# Paths that usually hold a product catalogue.
PRODUCT_HINTS = ("product", "shop", "portfolio", "brands", "range", "catalog")


def _key() -> str:
    key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not key:
        print("FIRECRAWL_API_KEY is not set. See .env.example.", file=sys.stderr)
        raise SystemExit(2)
    return key


def _post(client: httpx.Client, path: str, payload: dict) -> dict:
    r = client.post(f"{API}{path}", json=payload, timeout=120)
    if r.status_code == 429:
        time.sleep(20)
        r = client.post(f"{API}{path}", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def find_site(client: httpx.Client, manufacturer: str) -> str | None:
    """Search for the company's own website. Returns a domain root, or None."""
    # Strip legal suffixes — they rarely appear in the domain and hurt the search.
    name = re.sub(r"\b(limited|ltd|plc|inc|nigeria|industries|pharmaceuticals?|pharma)\b",
                  " ", manufacturer, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    data = _post(client, "/search", {
        "query": f"{manufacturer} official website products",
        "limit": 8,
    })
    for hit in data.get("data", {}).get("web", data.get("data", [])) or []:
        url = hit.get("url") or ""
        if not url or BLOCKED.search(url):
            continue
        host = urlparse(url).netloc.lower()
        # Require some overlap between the company name and the domain, so we do
        # not crawl an unrelated site that merely mentions the manufacturer.
        tokens = [t for t in re.split(r"[\s-]+", name.lower()) if len(t) > 3]
        if tokens and not any(t[:6] in host for t in tokens):
            continue
        return f"{urlparse(url).scheme}://{host}"
    return None


def product_urls(client: httpx.Client, site: str, limit: int) -> list[str]:
    data = _post(client, "/map", {"url": site, "search": "product", "limit": 120})
    links = data.get("links", data.get("data", {}).get("links", [])) or []
    urls = []
    for entry in links:
        u = entry.get("url") if isinstance(entry, dict) else entry
        if not u or u.endswith(".xml") or u.endswith(".rss"):
            continue
        if any(h in u.lower() for h in PRODUCT_HINTS):
            urls.append(u)
    # Category/listing pages carry many products per fetch — take those first.
    urls.sort(key=lambda u: (0 if "categor" in u.lower() or u.rstrip("/").endswith(("products", "shop")) else 1, len(u)))
    return urls[:limit]


def scrape(client: httpx.Client, url: str) -> dict | None:
    try:
        data = _post(client, "/scrape", {
            "url": url,
            "formats": ["markdown"],
            # onlyMainContent MUST stay False. It strips the product description
            # under each tile — which is where the NAFDAC number, dosage form and
            # pack size live. With it on, Afrab-Chem yielded 30 images and 0 NRNs;
            # with it off, the same page gives "_Syrup_ (NRN: A4-7551): Loratadine
            # 5 mg". Site chrome comes along too, but the parser already discards
            # logo/icon images, and losing identity fields is far worse than noise.
            "onlyMainContent": False,
            "waitFor": 3000,
        })
    except Exception as exc:
        print(f"    scrape failed: {str(exc)[:90]}")
        return None
    body = data.get("data", data)
    md = body.get("markdown") or ""
    return {"url": url, "markdown": md} if md else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manufacturer")
    ap.add_argument("--site", help="Skip discovery and crawl this site.")
    ap.add_argument("--pages", type=int, default=15, help="Max pages to scrape.")
    ap.add_argument("--delay", type=float, default=1.5, help="Seconds between pages.")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", args.manufacturer.lower()).strip("_")
    out = OUT_DIR / f"{slug}.json"

    with httpx.Client(headers={"Authorization": f"Bearer {_key()}"}) as client:
        site = args.site or find_site(client, args.manufacturer)
        if not site:
            print(f"NO SITE FOUND for {args.manufacturer!r}")
            return 1
        print(f"site   : {site}")

        urls = product_urls(client, site, args.pages)
        print(f"pages  : {len(urls)} product-ish URLs")
        if not urls:
            print("  no product pages discovered")
            return 1

        pages = []
        for i, u in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] {u[:88]}")
            page = scrape(client, u)
            if page:
                pages.append(page)
            time.sleep(args.delay)

    out.write_text(json.dumps(pages, indent=1), encoding="utf-8")
    print(f"\nsaved {len(pages)} pages -> {out}")
    print("next:")
    print(f'  python -m scripts.ingest_crawled_catalogue {out} '
          f'--manufacturer "{args.manufacturer}" --allow-brand-form')
    return 0


if __name__ == "__main__":
    sys.exit(main())
