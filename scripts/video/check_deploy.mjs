/** Smoke-check a deployed storefront. Usage: node scripts/video/check_deploy.mjs <base-url> [label] */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const URL = process.argv[2];
const LABEL = process.argv[3] ?? 'deploy';
mkdirSync('scripts/video/out/verify', { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const bad = [];
page.on('response', (r) => {
  if (r.status() >= 400) bad.push(`${r.status()} ${r.url().slice(0, 110)}`);
});
page.on('pageerror', (e) => bad.push(`pageerror: ${e.message}`));

await page.goto(`${URL}/shop`, { waitUntil: 'networkidle', timeout: 90000 });
await page.waitForTimeout(3000);

const info = await page.evaluate(() => ({
  title: document.title,
  productCount: document.body.innerText.match(/(\d+)\s+PRODUCTS/)?.[1] ?? 'not found',
  cards: document.querySelectorAll('a[href*="/shop/"]').length,
  productPhotos: [...document.querySelectorAll('img')].filter((i) => i.src.includes('/media/')).length,
  fallbackIcons: document.querySelectorAll('a[href*="/shop/"] svg').length,
}));

console.log(JSON.stringify(info, null, 2));
console.log('failed responses / page errors:', bad.length ? bad.slice(0, 8) : 'none');

await page.screenshot({ path: `scripts/video/out/verify/${LABEL}-shop.png` });
await browser.close();
