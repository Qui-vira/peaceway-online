/**
 * PHASE 0 verification probe — NOT part of the scraping pipeline.
 *
 * Answers one question per site: does this manufacturer publish photographs of the
 * actual product pack, or only logos and icons?
 *
 * Usage: node scripts/video/probe_manufacturer.mjs <url> "<Manufacturer Name>"
 */
import { chromium } from 'playwright';

const URL = process.argv[2];
const NAME = process.argv[3] ?? URL;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

let httpStatus = 0;
try {
  const resp = await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  httpStatus = resp?.status() ?? 0;
  await page.waitForTimeout(3500);
} catch (err) {
  console.log(JSON.stringify({ manufacturer: NAME, url: URL, ok: false, error: err.message.split('\n')[0] }));
  await browser.close();
  process.exit(0);
}

const result = await page.evaluate(() => {
  const imgs = [...document.querySelectorAll('img')];
  const isChrome = (s) => /logo|icon|favicon|banner|placeholder|avatar|sprite|flag/i.test(s);

  const candidates = imgs
    .map((i) => ({
      src: i.currentSrc || i.src,
      alt: (i.alt || '').trim(),
      w: i.naturalWidth,
      h: i.naturalHeight,
    }))
    // A pack photo is a real raster of meaningful size that isn't site chrome.
    .filter((i) => i.src && i.w >= 120 && i.h >= 120 && !isChrome(i.src) && !isChrome(i.alt));

  return {
    title: document.title,
    totalImgs: imgs.length,
    packPhotoCount: candidates.length,
    samples: candidates.slice(0, 4),
    // Do titles carry the strength/pack detail the matcher would need?
    strengthMentions: (document.body.innerText.match(/\b\d+\s?(mg|ml|mcg|g|IU)\b/gi) || []).slice(0, 8),
  };
});

console.log(JSON.stringify({ manufacturer: NAME, url: URL, httpStatus, ok: true, ...result }, null, 2));
await browser.close();
