/* M31: Playwright acceptance za reorganiziranu navigaciju.
   Pokretanje (nakon builda):
     npx vite preview --port 4173 &
     BASE_URL=http://localhost:4173 node tests/nav_acceptance.mjs
   Pokriva: otvaranje oba dropdowna (hover), navigaciju na SVAKU podstavku,
   klik na naziv grupe (navigira, nije mrtav gumb), aktivno naglašavanje
   roditelja, mobile hamburger + accordion (<=768px). */
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
  '--proxy-server=direct://', '--proxy-bypass-list=*'] // lokalni preview, bez proxyja
const browser = await chromium.launch(launchOpts)

/* ---------- desktop ---------- */
{
  const p = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  p.setDefaultTimeout(10000)
  const errs = []
  p.on('pageerror', (e) => errs.push(String(e)))
  await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('.hdr-nav a', { state: 'attached' })

  check('desktop: 3 grupe + DIONICA u navu',
    await p.locator('.hdr-nav > * > a, .hdr-nav > a').count() >= 4)

  // TRŽIŠTE dropdown: hover otvara, sadrži svih 5 podstavki
  const trziste = p.locator('.hdr-group', { hasText: 'TRŽIŠTE' })
  await trziste.hover()
  await p.waitForTimeout(150)
  check('TRŽIŠTE dropdown se otvara hoverom',
    await trziste.locator('.hdr-dd').isVisible())
  for (const [label, path] of [['Screener', '/screener'], ['Indeksi', '/indeksi'], ['Obveznice', '/obveznice'],
    ['Dividende', '/dividende'], ['Usporedba', '/usporedba'],
    ['Alati', '/alati'], ['Sve dionice', '/']]) {
    await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
    await p.waitForSelector('.hdr-nav a', { state: 'attached' })
    await p.locator('.hdr-group', { hasText: 'TRŽIŠTE' }).hover()
    await p.click(`.hdr-dd >> text=${label}`)
    await p.waitForTimeout(250)
    check(`TRŽIŠTE › ${label} -> ${path}`,
      new URL(p.url()).pathname === path, p.url())
  }

  // BLOG dropdown + podstavke
  await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
  const blog = p.locator('.hdr-group', { hasText: 'BLOG' })
  await blog.hover()
  await p.waitForTimeout(150)
  check('BLOG dropdown se otvara hoverom', await blog.locator('.hdr-dd').isVisible())
  for (const [label, path] of [['Vijesti', '/vijesti'], ['Blog', '/blog']]) {
    await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
    await p.waitForSelector('.hdr-nav a', { state: 'attached' })
    await p.locator('.hdr-group', { hasText: 'BLOG' }).hover()
    await p.click(`.hdr-dd >> text=${label}`)
    await p.waitForTimeout(250)
    check(`BLOG › ${label} -> ${path}`, new URL(p.url()).pathname === path, p.url())
  }

  // klik na SAM naziv grupe navigira (nije mrtav gumb)
  await p.goto(`${BASE}/screener`, { waitUntil: 'domcontentloaded' })
  await p.click('.hdr-group > a:has-text("TRŽIŠTE")')
  await p.waitForTimeout(250)
  check('klik na "TRŽIŠTE" navigira na /', new URL(p.url()).pathname === '/')
  await p.click('.hdr-group > a:has-text("BLOG")')
  await p.waitForTimeout(250)
  check('klik na "BLOG" navigira na /blog', new URL(p.url()).pathname === '/blog')

  // PORTFELJ samostalan (bez dropdowna)
  check('PORTFELJ nema dropdown',
    await p.locator('.hdr-group', { hasText: 'PORTFELJ' }).count() === 0
    && await p.locator('.hdr-nav a', { hasText: 'PORTFELJ' }).count() === 1)

  // aktivna ruta naglašava RODITELJA
  await p.goto(`${BASE}/dividende`, { waitUntil: 'domcontentloaded' })
  check('na /dividende roditelj TRŽIŠTE nosi .on',
    await p.locator('.hdr-group > a.on:has-text("TRŽIŠTE")').count() === 1)
  await p.goto(`${BASE}/vijesti`, { waitUntil: 'domcontentloaded' })
  check('na /vijesti roditelj BLOG nosi .on',
    await p.locator('.hdr-group > a.on:has-text("BLOG")').count() === 1)

  check('desktop bez JS grešaka', errs.length === 0, errs.join('; '))
  await p.close()
}

/* ---------- mobile (<=768px) ---------- */
{
  const p = await browser.newPage({ viewport: { width: 375, height: 720 } })
  p.setDefaultTimeout(10000)
  const errs = []
  p.on('pageerror', (e) => errs.push(String(e)))
  await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('.hdr-burger', { state: 'attached' })

  check('mobile: desktop nav skriven', !(await p.locator('.hdr-nav').isVisible()))
  check('mobile: hamburger vidljiv', await p.locator('.hdr-burger').isVisible())

  await p.click('.hdr-burger')
  check('mobile: panel se otvara', await p.locator('.hdr-mobile').isVisible())
  // TRŽIŠTE accordion je otvoren zadano; BLOG se rasklapa klikom
  check('mobile: TRŽIŠTE sekcija rasklopljena (7 stavki)',
    await p.locator('.hdr-mob-sub').count() === 7)
  await p.click('.hdr-mob-group button:has-text("BLOG")')
  check('mobile: BLOG accordion prikazuje Blog+Vijesti',
    await p.locator('.hdr-mob-sub').count() === 2)
  await p.click('.hdr-mob-sub:has-text("Vijesti")')
  await p.waitForTimeout(250)
  check('mobile: navigacija na /vijesti + panel se zatvara',
    new URL(p.url()).pathname === '/vijesti'
    && !(await p.locator('.hdr-mobile').isVisible()))
  // PORTFELJ dostupan kao direktna stavka
  await p.click('.hdr-burger')
  check('mobile: PORTFELJ direktna stavka',
    await p.locator('.hdr-mob-top:has-text("PORTFELJ")').count() === 1)

  check('mobile bez JS grešaka', errs.length === 0, errs.join('; '))
  await p.close()
}

await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} provjera prošlo`)
if (failed.length) process.exit(1)
