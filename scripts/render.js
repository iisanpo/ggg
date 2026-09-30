const { chromium } = require('playwright');
const [htmlPath, pdfPath, header, fg] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const p = await b.newPage();
  await p.goto('file://' + htmlPath, { waitUntil: 'load' });
  await p.emulateMedia({ media: 'print' });
  await p.waitForTimeout(400);
  const f = (s) => `<div style="font-family:'Noto Sans CJK KR',sans-serif;font-size:7.5pt;color:${fg || '#8B8980'};width:100%;padding:0 13mm;">${s}</div>`;
  await p.pdf({ path: pdfPath, format: 'A4', printBackground: true, displayHeaderFooter: true,
    headerTemplate: f(`<div style="text-align:right">${header}</div>`),
    footerTemplate: f('<div style="text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'),
    margin: { top: '14mm', bottom: '14mm', left: '13mm', right: '13mm' } });
  await b.close();
})();
