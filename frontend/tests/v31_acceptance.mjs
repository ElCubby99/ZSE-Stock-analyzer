/* v3.1: Playwright acceptance — dividendni pod + kompozitni g1.
   Pokretanje (nakon builda):
     npx vite preview --port 4173 &
     BASE_URL=http://localhost:4173 node tests/v31_acceptance.mjs
   Pokriva: HT stranica ima objavljenu fer-zonu, verdikt "PROLAZI (UZ
   DIVIDENDNI POD)" s raspisom, karticu kompozitnog g1 s tri signala;
   nigdje na stranici (ni na screeneru) nema "u rekalibraciji". */
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

{
  const p = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  p.setDefaultTimeout(15000)
  await p.goto(`${BASE}/dionica/ht`, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('h1', { state: 'attached' })
  // tab s analizom vrijednosti (button:has-text — text= presreće header)
  const tab = p.locator('button:has-text("ANALIZA VRIJEDNOSTI")').first()
  if (await tab.count()) await tab.click()
  await p.waitForTimeout(400)
  const body = await p.evaluate(() => document.body.innerText)

  check('HT: fer-zona objavljena (50,68 na stranici)',
    /50,68/.test(body))
  check('HT: verdikt "prolazi (uz dividendni pod)"',
    /PROLAZI \(UZ DIVIDENDNI POD\)/i.test(body))
  check('HT: raspis "Dividendni pod primijenjen" s brojkama',
    /Dividendni pod primijenjen/i.test(body))
  check('HT: kartica kompozitnog g1 (Rast eksplicitne faze)',
    /Rast eksplicitne faze g1 \(kompozit\)/i.test(body))
  check('HT: raspis signala — održivi rast + sidro terminala',
    /održivi rast \(ROE/i.test(body) && /sidro terminala/i.test(body))
  check('HT: TTM vs lani samo kontekst',
    /samo kontekst/i.test(body))
  check('HT: nema "u rekalibraciji"',
    !/u rekalibraciji/i.test(body))
  await p.close()
}

{
  const p = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  p.setDefaultTimeout(15000)
  await p.goto(`${BASE}/screener`, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('.scr-row', { state: 'attached' })
  const body = await p.evaluate(() => document.body.innerText)
  check('Screener: nema "u rekalibraciji"', !/u rekalibraciji/i.test(body))
  await p.close()
}

await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} OK`)
process.exit(failed.length ? 1 : 0)
