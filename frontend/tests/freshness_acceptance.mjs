/* M32: Playwright acceptance za formulaciju svježine podataka.
   Pokretanje (nakon builda):
     npx vite preview --port 4173 &
     BASE_URL=http://localhost:4173 node tests/freshness_acceptance.mjs
   Provjerava: "(dan zaostatka)" NIGDJE (naslovnica + stranica dionice +
   footer), header nosi stvarni datum exporta + "nakon zatvaranja". */
const BASE = process.env.BASE_URL || 'http://localhost:4173'

let chromium
try { ({ chromium } = await import('playwright')) } catch {
  ({ chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs'))
}

const results = []
const check = (name, ok, extra = '') => {
  results.push(ok)
  console.log(`${ok ? 'OK ' : 'FAIL'} ${name}${extra ? ` — ${extra}` : ''}`)
}

const browser = await chromium.launch({
  args: ['--no-sandbox', '--disable-dev-shm-usage',
    '--proxy-server=direct://', '--proxy-bypass-list=*'],
  ...(process.env.PLAYWRIGHT_CHROMIUM ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM }
    : (await import('node:fs')).existsSync('/opt/pw-browsers/chromium')
      ? { executablePath: '/opt/pw-browsers/chromium' } : {}),
})
const p = await browser.newPage()
p.setDefaultTimeout(10000)

// naslovnica
await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
await p.waitForSelector('.mk-title span')
let body = await p.locator('body').innerText()
check('naslovnica: nema "(dan zaostatka)"', !body.includes('dan zaostatka'))
const hdr = await p.locator('.mk-title span').innerText()
check('naslovnica: header nosi datum exporta (EOD za d.m.gggg.)',
  /EOD za \d{1,2}\.\s?\d{1,2}\.\s?\d{4}/.test(hdr.replace(/\s+/g, ' ')), hdr)
check('naslovnica: formulacija "nakon zatvaranja trgovine (16:00)"',
  hdr.includes('nakon zatvaranja trgovine (16:00)'))
check('footer: "ažuriraju nakon zatvaranja burze"',
  (await p.locator('footer').innerText()).includes('podaci se ažuriraju nakon zatvaranja burze'))

// stranica dionice (hidratirana)
await p.goto(`${BASE}/dionica/adrs`, { waitUntil: 'domcontentloaded' })
await p.waitForSelector('footer')
await p.waitForTimeout(600)
body = await p.locator('body').innerText()
check('dionica: nema "(dan zaostatka)"', !body.includes('dan zaostatka'))

// statički HTML dionice (ono što botovi/curl vide, bez JS-a); trailing slash
// jer lokalni vite preview ne rješava clean URL bez nje (Vercel rješava)
const raw = await (await fetch(`${BASE}/dionica/adrs/`)).text()
check('dionica (statički HTML): nema "dan zaostatka"', !raw.includes('dan zaostatka'))
check('dionica (statički HTML): "ažurira se nakon zatvaranja trgovine u 16:00"',
  raw.includes('ažurira se nakon zatvaranja trgovine u 16:00'))

await browser.close()
const failed = results.filter((ok) => !ok).length
console.log(`\n${results.length - failed}/${results.length} provjera prošlo`)
if (failed) process.exit(1)
