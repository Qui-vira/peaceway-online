/** Post-deploy production verification. node scripts/video/verify_prod.mjs */
import { chromium } from 'playwright';

const BASE = 'https://www.peacewayonline.com';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const errors = [];
page.on('pageerror', (e) => errors.push(`${page.url()} :: ${e.message}`));
page.on('response', (r) => {
  if (r.status() >= 400 && !r.url().includes('sentry')) errors.push(`${r.status()} ${r.url().slice(0, 100)}`);
});

const routes = ['/', '/shop', '/cart', '/checkout', '/prescription'];
for (const route of routes) {
  const resp = await page.goto(BASE + route, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1200);
  const words = (await page.locator('body').innerText()).split(/\s+/).filter(Boolean).length;
  console.log(`${String(resp?.status()).padEnd(4)} ${route.padEnd(16)} ${words} words`);
}

// A real product detail page, reached the way a customer would.
await page.goto(`${BASE}/shop`, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(1500);
const href = await page.getAttribute('a[href^="/shop/"]', 'href');
const detail = await page.goto(BASE + href, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(1200);
console.log(`${detail?.status()}  ${href}  (product detail)`);

// The new media route must exist and 404 cleanly for an unknown id.
const media = await page.request.get(`${BASE}/api/v1/media/00000000-0000-0000-0000-000000000000`);
console.log(`${media.status()}  /api/v1/media/<unknown>  (expect 404)`);

// image_url must be present on the wire, even while null.
const cat = await page.request.get(`${BASE}/api/v1/catalog?q=cal`);
const rows = await cat.json();
console.log(`${cat.status()}  /api/v1/catalog  image_url key present on all rows: ${rows.every((r) => 'image_url' in r)}`);

console.log('\nerrors:', errors.length ? errors.slice(0, 10) : 'none');
await browser.close();
