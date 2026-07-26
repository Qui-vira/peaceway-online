/**
 * Discovery pass for the Peaceway demo video.
 *
 * Visits every route on the LIVE site and reports what actually renders.
 * Records nothing. Invents nothing. Its only job is to tell us which shots
 * are real and which pages are broken/empty so we never film a dead screen.
 *
 * Run: node scripts/video/discover.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = 'https://www.peacewayonline.com';
const OUT = 'scripts/video/out/discover';

const ROUTES = [
  ['A1_landing', '/'],
  ['A3_shop', '/shop'],
  ['A8_ask_pharmacist', '/ask-pharmacist'],
  ['A9_prescription', '/prescription'],
  ['A10_orders', '/orders'],
  ['cart', '/cart'],
  ['checkout', '/checkout'],
  ['start', '/start'],
  ['request', '/request'],
];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await ctx.newPage();

const consoleErrors = [];
page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()));

mkdirSync(OUT, { recursive: true });
const report = [];

for (const [name, route] of ROUTES) {
  const url = BASE + route;
  const before = consoleErrors.length;
  let status = 'ok';
  let note = '';

  try {
    const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(1500);

    const httpStatus = resp?.status() ?? 0;
    const text = (await page.locator('body').innerText()).trim();
    const words = text.split(/\s+/).filter(Boolean).length;

    if (httpStatus >= 400) { status = 'HTTP_ERROR'; note = `http ${httpStatus}`; }
    else if (words < 25) { status = 'EMPTY'; note = `only ${words} words rendered`; }

    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });

    report.push({
      name, route, httpStatus, status, note,
      words,
      title: await page.title(),
      headings: await page.locator('h1, h2').allInnerTexts().catch(() => []),
      newConsoleErrors: consoleErrors.length - before,
      textSample: text.slice(0, 900),
    });
  } catch (err) {
    report.push({ name, route, status: 'FAILED', note: err.message.split('\n')[0] });
  }
}

// Pull REAL product names off the live shop so the search shot uses a real
// medicine, never an invented one.
let products = [];
try {
  await page.goto(BASE + '/shop', { waitUntil: 'networkidle', timeout: 45000 });
  await page.waitForTimeout(2500);
  products = await page.evaluate(() => {
    const out = [];
    // Anything linking into a product detail route is a real catalog item.
    document.querySelectorAll('a[href*="/shop/"]').forEach((a) => {
      const t = a.innerText.trim().replace(/\s+/g, ' ');
      if (t) out.push({ text: t.slice(0, 160), href: a.getAttribute('href') });
    });
    return out;
  });
} catch (err) {
  products = [{ error: err.message.split('\n')[0] }];
}

writeFileSync(`${OUT}/report.json`, JSON.stringify({ base: BASE, report, products, consoleErrors: consoleErrors.slice(0, 30) }, null, 2));

console.log('=== ROUTE REPORT ===');
for (const r of report) {
  console.log(`${r.status.padEnd(11)} ${r.route.padEnd(18)} http=${r.httpStatus ?? '-'} words=${r.words ?? '-'} errs=${r.newConsoleErrors ?? '-'} ${r.note}`);
  if (r.headings?.length) console.log(`            headings: ${r.headings.slice(0, 5).join(' | ').slice(0, 200)}`);
}
console.log(`\n=== REAL PRODUCTS FOUND ON /shop: ${products.length} ===`);
products.slice(0, 25).forEach((p) => console.log(' -', p.text ?? p.error, p.href ?? ''));

await browser.close();
