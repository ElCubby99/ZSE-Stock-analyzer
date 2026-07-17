/* M38: Playwright acceptance za englesku verziju (/en).
   Pokretanje (nakon builda):
     npx vite preview --port 4173 &
     BASE_URL=http://localhost:4173 node tests/m38_acceptance.mjs
   Pokriva: jezični switcher u headeru (dionica, screener, dividende —
   oba smjera, ista stranica drugi jezik), EN SPA sadržaj stranice
   dionice (tabovi, pokazatelji, disclaimer na engleskom, html lang),
   dvojezični cookie banner. */
const BASE = process.env.BASE_URL || 'http://localhost:4173'

let chromium
try { ({ chromium } = await import('playwright')) } catch {
  ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs'))
}

const results = []
const check = (name, ok, extra = '') => {
  results.push({ name, ok })
  console.log(`${ok ? 'OK ' : 'FAIL'} ${name}${extra ? ` — ${extra}` : ''}`)
}

const launchOpts = process.env.PLAYWRIGHT_CHROMIUM
  ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM } : {}
if (!launchOpts.executablePath) {
  try { const fs = await import('node:fs'); if (fs.existsSync('/opt/pw-browsers/chromium')) launchOpts.executablePath = '/opt/pw-browsers/chromium' } catch { /* default */ }
}
launchOpts.args = ['--no-sandbox', '--disable-dev-shm-usage',
  '--proxy-server=direct://', '--proxy-bypass-list=*']
const browser = await chromium.launch(launchOpts)

const page = async () => {
  const p = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  p.setDefaultTimeout(12000)
  await p.route('**googletagmanager.com/**', (r) => r.abort())
  return p
}

/* ---------- switcher: HR -> EN -> HR na dionici ---------- */
{
  const p = await page()
  await p.goto(`${BASE}/dionica/koei`, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('.hdr-lang', { state: 'attached' })
  await p.click('.hdr-lang >> text=EN')
  await p.waitForTimeout(400)
  check('switcher dionica HR->EN', new URL(p.url()).pathname === '/en/stock/koei', p.url())
  check('html lang=en nakon prelaska', await p.evaluate(() => document.documentElement.lang) === 'en')
  await p.click('.hdr-lang >> text=HR')
  await p.waitForTimeout(400)
  check('switcher dionica EN->HR', new URL(p.url()).pathname === '/dionica/koei', p.url())
  await p.close()
}

/* ---------- switcher: screener i dividende ---------- */
for (const [hr, en] of [['/screener', '/en/screener'], ['/dividende', '/en/dividends']]) {
  const p = await page()
  await p.goto(`${BASE}${hr}`, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('.hdr-lang', { state: 'attached' })
  await p.click('.hdr-lang >> text=EN')
  await p.waitForTimeout(400)
  check(`switcher ${hr} -> ${en}`, new URL(p.url()).pathname === en, p.url())
  await p.click('.hdr-lang >> text=HR')
  await p.waitForTimeout(400)
  check(`switcher ${en} -> ${hr}`, new URL(p.url()).pathname === hr, p.url())
  await p.close()
}

/* ---------- EN SPA sadržaj stranice dionice ---------- */
{
  const p = await page()
  const errs = []
  p.on('pageerror', (e) => errs.push(String(e)))
  await p.goto(`${BASE}/en/stock/koei`, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('.stab button', { state: 'attached' })
  const tabs = await p.locator('.stab button').allTextContents()
  check('EN tabovi (OVERVIEW/VALUATION ANALYSIS...)',
    tabs.includes('OVERVIEW') && tabs.includes('VALUATION ANALYSIS'), tabs.join('|'))
  await p.click('.stab button >> text=KEY INDICATORS')
  await p.waitForSelector('.ind-card h4', { state: 'attached' })
  const groups = await p.locator('.ind-card h4').allTextContents()
  check('EN naslovi grupa pokazatelja',
    groups.includes('Valuation') && groups.includes('Share performance'), groups.join('|'))
  const disc = await p.locator('.disc').first().textContent()
  check('EN disclaimer', /not investment advice/i.test(disc || ''), (disc || '').slice(0, 60))
  const body = await p.locator('#root').textContent()
  check('bez sirovih i18n ključeva u DOM-u', !/\b(sp|mp|ab|ind|ki|cmpS|lg|vs|mn|nt|gp)\.[a-zA-Z]/.test(body || ''))
  check('bez JS grešaka na /en/stock/koei', errs.length === 0, errs.join('; ').slice(0, 120))
  await p.close()
}

/* ---------- cookie banner dvojezičan ---------- */
{
  const p = await page()
  await p.goto(`${BASE}/en`, { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(600)
  const banner = await p.locator('body').textContent()
  check('EN cookie banner (accept/cookies na engleskom)',
    /cookie/i.test(banner || '') && !/kolači/i.test((await p.locator('.cc-banner, [class*=consent], [class*=cookie]').first().textContent().catch(() => '')) || ''))
  await p.close()
}

await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} OK`)
if (failed.length) { console.error('PADOVI:', failed.map((f) => f.name).join(' | ')); process.exit(1) }
