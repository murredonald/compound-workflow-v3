const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  const b = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const p = await b.newPage();
  await p.setViewport({ width: 1200, height: 800, deviceScaleFactor: 2 });

  const html = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'temp', 'm02-number-grid.html'), 'utf8');
  const outDir = path.join(__dirname, '..', '..', 'public', 'blog', 'belgische-markt-fiscale-ai');

  // Dark variant
  await p.setContent(html, { waitUntil: 'domcontentloaded' });
  await new Promise(r => setTimeout(r, 500));
  const el = await p.$('.graphic');
  const box = await el.boundingBox();
  await el.screenshot({ path: path.join(outDir, 'belgian-tax-ai-gap-numbers-dark.png') });
  console.log('Dark done:', Math.round(box.width) + 'x' + Math.round(box.height));

  // Light variant
  const lightHtml = html.replace('<body>', '<body class="light">');
  await p.setContent(lightHtml, { waitUntil: 'domcontentloaded' });
  await new Promise(r => setTimeout(r, 500));
  const el2 = await p.$('.graphic');
  await el2.screenshot({ path: path.join(outDir, 'belgian-tax-ai-gap-numbers-light.png') });
  console.log('Light done');

  await b.close();
})();
