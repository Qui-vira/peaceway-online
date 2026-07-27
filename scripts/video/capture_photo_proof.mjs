/** Capture proof that a real manufacturer photo renders on the live storefront. */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const OUT = 'scripts/video/out/proof';
const PRODUCT_ID = process.argv[2];
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

// Shop grid, searched down to the one product so the card is unambiguous.
await page.goto('https://www.peacewayonline.com/shop', { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(1500);
const search = page.locator('input[placeholder*="Search"]').first();
await search.fill('Feroglobin');
await page.waitForTimeout(3000);
await page.screenshot({ path: `${OUT}/shop-with-photo.png` });

// Did an <img> actually paint, and is it served from our media endpoint?
const audit = await page.evaluate(() => {
  const imgs = [...document.querySelectorAll('img')].filter((i) => i.src.includes('/media/'));
  return imgs.map((i) => ({
    src: i.src, alt: i.alt, w: i.naturalWidth, h: i.naturalHeight, complete: i.complete,
  }));
});

await page.goto(`https://www.peacewayonline.com/shop/${PRODUCT_ID}`, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(2500);
await page.screenshot({ path: `${OUT}/detail-with-photo.png` });

console.log('product images rendered on /shop:', JSON.stringify(audit, null, 2));
await browser.close();
