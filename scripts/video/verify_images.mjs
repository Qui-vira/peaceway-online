/** Screenshot the local storefront to confirm photo + icon-fallback both render. */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const OUT = 'scripts/video/out/verify';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const failed = [];
page.on('requestfailed', (r) => failed.push(`${r.failure()?.errorText} ${r.url()}`));
page.on('response', (r) => {
  if (r.url().includes('/media/') && r.status() !== 200) failed.push(`HTTP ${r.status()} ${r.url()}`);
});

await page.goto('http://localhost:3000/shop', { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(2000);
await page.screenshot({ path: `${OUT}/shop.png` });

// Did an <img> actually paint, and did the other card keep its SVG icon?
const audit = await page.evaluate(() => {
  const imgs = [...document.querySelectorAll('img')].filter((i) => i.src.includes('/media/'));
  return {
    productImages: imgs.map((i) => ({
      src: i.src.split('/media/')[1],
      naturalWidth: i.naturalWidth,
      naturalHeight: i.naturalHeight,
      complete: i.complete,
      alt: i.alt,
    })),
    svgIconCount: document.querySelectorAll('a[href*="/shop/"] svg').length,
  };
});

const href = await page.getAttribute('a[aria-label="Afrab Loratadine Syrup"]', 'href');
await page.goto(`http://localhost:3000${href}`, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/detail.png` });

console.log('product <img> elements:', JSON.stringify(audit.productImages, null, 2));
console.log('fallback SVG icons still rendering:', audit.svgIconCount);
console.log('failed requests:', failed.length ? failed : 'none');

await browser.close();
