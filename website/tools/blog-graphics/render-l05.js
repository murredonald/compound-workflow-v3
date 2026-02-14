const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  const b = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const p = await b.newPage();
  await p.setViewport({ width: 1200, height: 800, deviceScaleFactor: 2 });

  const html = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'temp', 'l05-before-after.html'), 'utf8');
  const outDir = path.join(__dirname, '..', '..', 'public', 'blog', 'meertaligheid-belgisch-fiscaal-recht');

  fs.mkdirSync(outDir, { recursive: true });

  // Dark variant
  await p.setContent(html, { waitUntil: 'domcontentloaded' });
  await new Promise(r => setTimeout(r, 500));
  const el = await p.$('.graphic');
  const box = await el.boundingBox();
  await el.screenshot({ path: path.join(outDir, 'monolingual-vs-bilingual-search-dark.png') });
  console.log('Dark done:', Math.round(box.width) + 'x' + Math.round(box.height));

  // Light variant
  const lightHtml = html.replace('<body>', '<body class="light">');
  await p.setContent(lightHtml, { waitUntil: 'domcontentloaded' });
  await new Promise(r => setTimeout(r, 500));
  const el2 = await p.$('.graphic');
  await el2.screenshot({ path: path.join(outDir, 'monolingual-vs-bilingual-search-light.png') });
  console.log('Light done');

  await b.close();
})();
