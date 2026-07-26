"""Shared fetch machinery for manufacturer scrapers.

Scrapling 0.4.11 does NOT expose a `robots_txt_obey` option and `adaptive` is a
class-level setting rather than a fetch argument, so both are handled here:

  * robots.txt is fetched once per domain and enforced with Protego (the parser
    Scrapy uses, which ships as a Scrapling dependency) before any page is fetched.
    A disallowed URL is skipped, not fetched.
  * A hard 3-second-per-domain gap is enforced between requests. If a site declares
    a longer Crawl-delay, that wins.

Lives under scripts/ because .railwayignore keeps scripts/ out of the deployed
container — scraping is an operator task run locally, never in the web dyno.
"""
from __future__ import annotations

import asyncio
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from protego import Protego
from scrapling.fetchers import StealthyFetcher

# Adaptive selectors: Scrapling relocates an element when a site's markup shifts,
# instead of silently returning nothing. Class-level in 0.4.11.
StealthyFetcher.configure(adaptive=True)

USER_AGENT = "PeacewayCatalogBot"
MIN_DELAY_SECONDS = 3.0

_last_request_at: dict[str, float] = {}
_robots_cache: dict[str, Protego | None] = {}


@dataclass
class FetchOutcome:
    url: str
    ok: bool
    page: object | None = None
    skipped_reason: str | None = None


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def _robots_for(domain: str) -> Protego | None:
    """Parsed robots.txt for a domain, or None when the site publishes none."""
    if domain in _robots_cache:
        return _robots_cache[domain]
    try:
        req = urllib.request.Request(
            f"https://{domain}/robots.txt", headers={"User-Agent": USER_AGENT}
        )
        body = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
        _robots_cache[domain] = Protego.parse(body)
    except urllib.error.HTTPError:
        # No robots.txt published (404) means nothing is disallowed.
        _robots_cache[domain] = None
    except Exception:
        # Network trouble reading robots is NOT permission to crawl. Fail closed.
        _robots_cache[domain] = Protego.parse("User-agent: *\nDisallow: /")
    return _robots_cache[domain]


def allowed(url: str) -> bool:
    rp = _robots_for(_domain(url))
    return True if rp is None else rp.can_fetch(url, USER_AGENT)


async def _throttle(domain: str) -> None:
    rp = _robots_for(domain)
    delay = MIN_DELAY_SECONDS
    if rp is not None:
        declared = rp.crawl_delay(USER_AGENT)
        if declared:
            delay = max(delay, float(declared))

    last = _last_request_at.get(domain)
    if last is not None:
        wait = delay - (time.monotonic() - last)
        if wait > 0:
            await asyncio.sleep(wait)
    _last_request_at[domain] = time.monotonic()


async def fetch(url: str, *, wait_selector: str | None = None, timeout: int = 45000) -> FetchOutcome:
    """Fetch one page, honouring robots.txt and the per-domain rate limit.

    Uses StealthyFetcher.async_fetch, not .fetch: the orchestrator runs under
    asyncio (it shares the app's async SQLAlchemy session), and Scrapling's sync
    fetch drives the sync Playwright API, which refuses to run inside a loop.
    """
    if not allowed(url):
        return FetchOutcome(url=url, ok=False, skipped_reason="disallowed by robots.txt")

    await _throttle(_domain(url))
    try:
        page = await StealthyFetcher.async_fetch(
            url,
            headless=True,
            network_idle=True,
            timeout=timeout,
            **({"wait_selector": wait_selector} if wait_selector else {}),
        )
    except Exception as exc:
        return FetchOutcome(url=url, ok=False, skipped_reason=f"fetch failed: {exc}")

    status = getattr(page, "status", 200)
    if status >= 400:
        return FetchOutcome(url=url, ok=False, skipped_reason=f"HTTP {status}")
    return FetchOutcome(url=url, ok=True, page=page)


def absolute(base: str, src: str | None) -> str | None:
    """Resolve a possibly-relative image src against its page URL."""
    if not src:
        return None
    src = src.strip()
    if src.startswith(("http://", "https://")):
        return src
    if src.startswith("//"):
        return "https:" + src
    parsed = urlparse(base)
    if src.startswith("/"):
        return f"{parsed.scheme}://{parsed.netloc}{src}"
    return f"{parsed.scheme}://{parsed.netloc}/{src.lstrip('./')}"
