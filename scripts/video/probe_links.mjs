/** PHASE 0 helper — list candidate product-listing links on a manufacturer site. */
import { chromium } from 'playwright';

const URL = process.argv[2];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

try {
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(3000);
} catch (e) {
  console.log('FETCH FAILED:', e.message.split('\n')[0]);
  await browser.close();
  process.exit(0);
}

const links = await page.evaluate(() =>
  [...new Set(
    [...document.querySelectorAll('a[href]')]
      .map((a) => a.href)
      .filter((h) => /product|shop|brand|range|portfolio|catalog/i.test(h))
  )].slice(0, 40)
);

console.log(links.join('\n') || '(no product-ish links found)');
await browser.close();
