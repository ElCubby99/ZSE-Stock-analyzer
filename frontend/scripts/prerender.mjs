/* M25 DIO 2: prerender / SSG-light — pokreće se NAKON `vite build`.
   Za svaku dionicu, blog post i statičku stranicu generira vlastiti
   dist/<ruta>/index.html s: <title>, meta description, canonical, OG/Twitter,
   JSON-LD (BreadcrumbList / FAQPage) i STATIČKIM sadržajem u #root (botovi i
   curl vide ime firme, cijenu i fer-zonu bez izvršavanja JS-a; React na
   hydrateu zamijeni sadržaj). Regenerira i sitemap.xml s lastmod = EOD datum.

   Ovo je svjesno "manja opcija" umjesto migracije na Next.js/vite-ssg:
   nula novih ovisnosti, build ostaje isti, sav sadržaj dolazi iz istih
   statičkih JSON exporta koje SPA ionako koristi.

   Popis ruta dolazi ISKLJUČIVO iz src/routes/registry.mjs — istog registryja
   iz kojeg router (main.jsx) gradi rute. Ova skripta NEMA vlastitu listu
   ruta: nova stranica registrirana u registryju automatski dobiva prerender
   i ulazi u sitemap (indexable: true) bez diranja ove skripte. */
import { promises as fs } from 'node:fs'
import { readFileSync } from 'node:fs'
const fsSyncRead = (p2) => readFileSync(p2, 'utf8')
import path from 'node:path'
import { ROUTES } from '../src/routes/registry.mjs'
import { SECTOR_EN, SECTOR_HR } from '../src/sectorLabels.mjs'
import { STR } from '../src/i18n/strings.mjs'
// M33: SSR bundle pravnih stranica (isti React sadržaj kao SPA, jedan izvor)
import { renderStatic } from '../dist-ssr/prerender-entry.js'

const DIST = path.resolve(process.cwd(), 'dist')
// Kanonska domena je www (site se i poslužuje na www; non-www 308-a na www) —
// canonical/sitemap/robots MORAJU biti na istoj varijanti, inače crawl put
// ide kroz nepotrebnu redirekciju i signali se miješaju.
const SITE = 'https://www.burzovnilist.com'
// M38: prijevodi iz i18n rječnika (jedan izvor istine) + sektori po jeziku
const tt = (key, lang) => (STR[key] ? (STR[key][lang] || STR[key].hr) : key)
const SEC = (key, lang) => ((lang === 'en' ? SECTOR_EN : SECTOR_HR)[key] || key || 'n/p')

const template = await fs.readFile(path.join(DIST, 'index.html'), 'utf8')
const overview = JSON.parse(await fs.readFile(path.join(DIST, 'data/overview.json'), 'utf8'))

const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
// M38: centralna format funkcija po jeziku — PRLOC postavljaju EN blokovi
let PRLOC = 'hr-HR'
const num = (v, d = 2) => (v === null || v === undefined || Number.isNaN(v)
  ? null
  : Number(v).toLocaleString(PRLOC, { minimumFractionDigits: d, maximumFractionDigits: d }))
const withLang = (lang, fn) => {
  const prev = PRLOC
  PRLOC = lang === 'en' ? 'en-GB' : 'hr-HR'
  try { return fn() } finally { PRLOC = prev }
}

/* M33: jedinstveni statički footer na SVIM prerendered rutama — crawleri
   moraju moći otkriti pravne stranice s bilo koje rute (trust/compliance).
   "Postavke kolačića" bez JS-a vodi na /politika-kolacica (panel radi tek
   s JS-om); React na hydrateu zamijeni sadržaj pravim footerom. */
const X_HANDLE = String(process.env.VITE_X_HANDLE || '').replace(/^@/, '')
const staticFooter = (lang = 'hr') => (lang === 'en' ? `
  <footer>
    <p>${esc(tt('common.disclaimerLong', 'en'))}</p>
    <p>© 2026 Burzovni list · <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a> ·
    <a href="/impressum">Impressum</a> · <a href="/en/methodology">Methodology</a> ·
    <a href="/en/terms">Terms of Use</a> ·
    <a href="/en/privacy">Privacy Policy</a> ·
    <a href="/en/cookies">Cookie Policy</a> ·
    <a href="/en/cookies">Cookie settings</a>${X_HANDLE ? ` ·
    <a href="https://x.com/${esc(X_HANDLE)}" rel="noopener noreferrer">X: @${esc(X_HANDLE)}</a>` : ''}</p>
    <p><a href="/en">All stocks</a> · <a href="/en/screener">Screener</a> ·
    <a href="/en/dividends">Dividends</a> · <a href="/en/comparison">Comparison</a> ·
    <a href="/en/news">News</a> ·
    ${esc(tt('common.freshness', 'en'))}</p>
  </footer>` : `
  <footer>
    <p>Prikazani podaci, rasponi i fer-zone su informativni i analitički — ne
    predstavljaju investicijski savjet, preporuku ni poticaj na trgovanje.
    Vrijednosti ilikvidnih dionica su indikativne. Zaključak je uvijek vaš.</p>
    <p>© 2026 Burzovni list · <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a> ·
    <a href="/impressum">Impressum</a> · <a href="/metodologija">Metodologija</a> ·
    <a href="/uvjeti-koristenja">Uvjeti korištenja</a> ·
    <a href="/politika-privatnosti">Politika privatnosti</a> ·
    <a href="/politika-kolacica">Politika kolačića</a> ·
    <a href="/politika-kolacica">Postavke kolačića</a>${X_HANDLE ? ` ·
    <a href="https://x.com/${esc(X_HANDLE)}" rel="noopener noreferrer">X: @${esc(X_HANDLE)}</a>` : ''}</p>
    <p><a href="/">Sve dionice</a> · <a href="/screener">Screener</a> ·
    <a href="/dividende">Dividende</a> · <a href="/usporedba">Usporedba</a> ·
    <a href="/vijesti">Vijesti</a> · <a href="/blog">Blog</a> ·
    Izvor: ZSE službeni EOD · podaci se ažuriraju nakon zatvaranja burze</p>
  </footer>`)

function page({ title, description, canonical, robots, extraHead = '', body = '',
  ogType = 'website', published = null, modified = null,
  lang = 'hr', alternates = null }) {
  let html = template
  html = html.replace(/<title>[\s\S]*?<\/title>/, `<title>${esc(title)}</title>`)
  html = html.replace(/<meta name="description" content="[^"]*" \/>/,
    `<meta name="description" content="${esc(description)}" />`)
  const head = [
    `<link rel="canonical" href="${canonical}" />`,
    // M38: hreflang parovi — canonical je po JEZIKU (EN na sebe), x-default HR
    alternates ? `<link rel="alternate" hreflang="hr" href="${alternates.hr}" />` : '',
    alternates ? `<link rel="alternate" hreflang="en" href="${alternates.en}" />` : '',
    alternates ? `<link rel="alternate" hreflang="x-default" href="${alternates.hr}" />` : '',
    robots ? `<meta name="robots" content="${robots}" />` : '',
    `<meta property="og:type" content="${ogType}" />`,
    // og:type=article nosi i datume objave/izmjene (blog i vijesti)
    ogType === 'article' && published
      ? `<meta property="article:published_time" content="${esc(published)}" />` : '',
    ogType === 'article' && (modified || published)
      ? `<meta property="article:modified_time" content="${esc(modified || published)}" />` : '',
    `<meta property="og:site_name" content="Burzovni list" />`,
    `<meta property="og:title" content="${esc(title)}" />`,
    `<meta property="og:description" content="${esc(description)}" />`,
    `<meta property="og:url" content="${canonical}" />`,
    `<meta property="og:image" content="${SITE}/og-default.png" />`,
    `<meta property="og:locale" content="${lang === 'en' ? 'en_GB' : 'hr_HR'}" />`,
    `<meta name="twitter:card" content="summary_large_image" />`,
    `<meta name="twitter:title" content="${esc(title)}" />`,
    `<meta name="twitter:description" content="${esc(description)}" />`,
    `<meta name="twitter:image" content="${SITE}/og-default.png" />`,
    extraHead,
  ].filter(Boolean).join('\n  ')
  html = html.replace('</head>', `  ${head}\n</head>`)
  // statički sadržaj u #root — React ga na mountu zamijeni; footer IDE NA
  // SVAKU rutu (M33), i onu bez vlastitog bodyja
  html = html.replace('<html lang="hr">', `<html lang="${lang}">`)
  html = html.replace('<div id="root"></div>',
    `<div id="root">${body}${staticFooter(lang)}</div>`)
  return html
}

async function write(route, html) {
  const dir = path.join(DIST, route)
  await fs.mkdir(dir, { recursive: true })
  await fs.writeFile(path.join(dir, 'index.html'), html)
}

const jsonLd = (obj) => `<script type="application/ld+json">${JSON.stringify(obj)}</script>`

/* ---------- dionice ---------- */
// overview.stocks je po KLASI; grupiraj po firmi (company), primarna klasa prva
const byCompany = new Map()
for (const s of overview.stocks) {
  if (!byCompany.has(s.company)) byCompany.set(s.company, s)
}
const eod = overview.stocks.find((s) => s.date)?.date || null
const urls = [] // za sitemap

function zoneText(s) {
  if (s.zone_low === null || s.zone_low === undefined || !s.price) return null
  const lo = num(s.zone_low, 0); const hi = num(s.zone_high, 0)
  let pos = 'u zoni'
  if (s.price > s.zone_high) pos = `${num((s.price / s.zone_high - 1) * 100, 1)} % iznad zone`
  else if (s.price < s.zone_low) pos = `${num((1 - s.price / s.zone_low) * 100, 1)} % ispod zone`
  return { lo, hi, pos }
}

let nStocks = 0
async function buildStockPages() {
for (const [company, s] of byCompany) {
  let data = null
  try {
    data = JSON.parse(await fs.readFile(path.join(DIST, `data/${company}.json`), 'utf8'))
  } catch { continue } // bez exporta nema stranice
  const t = company.toLowerCase()
  const name = data.name || company
  const z = zoneText(s)
  const price = num(s.price)
  // redoslijed = prioritet (odbacuje se s kraja): cijena i fer-zona ostaju
  const descParts = [
    price ? `Cijena ${price} €${s.date ? ` (${s.date})` : ''}` : null,
    z ? `fer-zona ${z.lo}–${z.hi} € (${z.pos})` : null,
    s.change_pct !== null && s.change_pct !== undefined
      ? `promjena ${num(s.change_pct * 100, 2)} %` : null,
    data.sector ? `sektor: ${data.sector}` : null,
  ].filter(Boolean)
  // <=155 znakova BEZ rezanja usred riječi: odbacuj zadnje dijelove dok stane
  let description = ''
  for (let parts = [...descParts]; ; parts.pop()) {
    description = `${company} — ${name}. ${parts.join(' · ')}. Nije investicijski savjet.`
    if (description.length <= 155 || !parts.length) break
  }
  if (description.length > 155) description = `${description.slice(0, 152)}…`
  const canonical = `${SITE}/dionica/${t}`

  const lastDiv = (data.dividends?.events || data.dividends || [])
  const divRow = Array.isArray(lastDiv)
    ? lastDiv.find((d) => d.amount_eur) : null

  const body = `
    <main>
      <nav><a href="/">Naslovnica</a> › <a href="/screener">Dionice</a> › ${esc(company)}</nav>
      <h1>${esc(name)} (${esc(company)}) — analiza dionice</h1>
      <h2>Cijena dionice</h2>
      <p>${price ? `Zadnja cijena: <strong>${price} €</strong>${s.date ? ` (službeni EOD za ${esc(s.date)} · ažurira se nakon zatvaranja trgovine u 16:00)` : ''}.` : 'Cijena trenutno nije dostupna.'}</p>
      ${z ? `<h2>Fer vrijednost (fer-zona)</h2>
      <p>Naša procjena fer-zone: <strong>${z.lo}–${z.hi} €</strong>; tržišna cijena je ${z.pos}. Fer-zona je informativan, činjenični prikaz iz javno opisane <a href="/metodologija">metodologije</a> — nije preporuka.</p>` : ''}
      ${divRow ? `<h2>Dividenda</h2>
      <p>Zadnja poznata dividenda: ${num(divRow.amount_eur)} € po dionici${divRow.ex_date ? ` (ex-datum ${esc(divRow.ex_date)})` : ''}. Vidi <a href="/dividende">kalendar dividendi</a>.</p>` : ''}
      <p>${data.sector ? `Sektor: ${esc(data.sector)}. ` : ''}Detaljna analiza vrijednosti, ključni pokazatelji, izvještaji i dioničari dostupni su na ovoj stranici (učitava se aplikacija).</p>
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p>
    </main>`

  const bc = jsonLd({
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Naslovnica', item: SITE },
      { '@type': 'ListItem', position: 2, name: 'Dionice', item: `${SITE}/screener` },
      { '@type': 'ListItem', position: 3, name: `${company} — ${name}`, item: canonical },
    ],
  })

  const canonicalEn = `${SITE}/en/stock/${t}`
  const alternates = { hr: canonical, en: canonicalEn }
  await write(`dionica/${t}`, page({
    title: `${company} dionica — ${name} | cijena, analiza vrijednosti, fer-zona | Burzovni list`,
    description, canonical, extraHead: bc, body, alternates,
  }))
  urls.push({ loc: canonical, lastmod: s.date || eod, alt: alternates })

  // M38: engleska varijanta — isti podaci, prevedeni predlošci narativa
  PRLOC = 'en-GB'
  const zEn = z && { ...z, pos: s.price > s.zone_high
    ? `${num((s.price / s.zone_high - 1) * 100, 1)}% above the zone`
    : s.price < s.zone_low
      ? `${num((1 - s.price / s.zone_low) * 100, 1)}% below the zone`
      : 'inside the zone' }
  const descEnParts = [
    price ? `Price €${price}${s.date ? ` (${s.date})` : ''}` : null,
    zEn ? `fair-value zone €${zEn.lo}–${zEn.hi} (${zEn.pos})` : null,
    data.sector ? `sector: ${SEC(data.sector, 'en')}` : null,
  ].filter(Boolean)
  let descriptionEn = ''
  for (let parts = [...descEnParts]; ; parts.pop()) {
    descriptionEn = `${company} — ${name}. ${parts.join(' · ')}. Not investment advice.`
    if (descriptionEn.length <= 155 || !parts.length) break
  }
  if (descriptionEn.length > 155) descriptionEn = `${descriptionEn.slice(0, 152)}…`
  const bodyEn = `
    <main>
      <nav><a href="/en">Home</a> › <a href="/en/screener">Stocks</a> › ${esc(company)}</nav>
      <h1>${esc(name)} (${esc(company)}) — stock analysis</h1>
      <h2>Share price</h2>
      <p>${price ? `Last price: <strong>€${price}</strong>${s.date ? ` (official end-of-day close for ${esc(s.date)} · updated after the 16:00 CET close)` : ''}.` : 'The price is currently unavailable.'}</p>
      ${zEn ? `<h2>Fair value (fair-value zone)</h2>
      <p>Our fair-value zone estimate: <strong>€${zEn.lo}–${zEn.hi}</strong>; the market price is ${zEn.pos}. The fair-value zone is a factual, informational output of our publicly described <a href="/en/methodology">methodology</a> — not a recommendation.</p>` : ''}
      ${divRow ? `<h2>Dividend</h2>
      <p>Last known dividend: €${num(divRow.amount_eur)} per share${divRow.ex_date ? ` (ex-date ${esc(divRow.ex_date)})` : ''}. See the <a href="/en/dividends">dividend calendar</a>.</p>` : ''}
      <p>${data.sector ? `Sector: ${esc(SEC(data.sector, 'en'))}. ` : ''}Detailed valuation analysis, key indicators, reports and shareholders are available on this page (the application loads on top of this content).</p>
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p>
    </main>`
  await write(`en/stock/${t}`, page({
    title: `${company} stock — ${name} | price, valuation, fair-value zone | Burzovni list`,
    description: descriptionEn, canonical: canonicalEn,
    lang: 'en', alternates, body: bodyEn,
  }))
  urls.push({ loc: canonicalEn, lastmod: s.date || eod, alt: alternates })
  PRLOC = 'hr-HR'
  nStocks += 1
}
}

/* ---------- M37: financije (as-reported izvještaji) ---------- */
let nFin = 0
async function buildFinPages() {
  const finFmt = (v, unit) => (v === null || v === undefined ? '—'
    : (unit === 'mil' ? v / 1e6 : v / 1e3).toLocaleString(PRLOC,
      { minimumFractionDigits: unit === 'mil' ? 1 : 0,
        maximumFractionDigits: unit === 'mil' ? 1 : 0 }))
  for (const [company] of byCompany) {
    let fin = null
    try {
      fin = JSON.parse(await fs.readFile(path.join(DIST, `data/fin/${company}.json`), 'utf8'))
    } catch { continue } // bez fin exporta nema stranice
    const t = company.toLowerCase()
    const basis = fin.bases[0]
    const ann = fin.views[basis] && fin.views[basis].annual
    if (!ann) continue
    const canonical = `${SITE}/dionica/${t}/financije`
    const unitTxt = fin.unit === 'mil' ? 'u milijunima EUR' : 'u tisućama EUR'
    const tableFor = (st) => {
      const tbl = ann.statements[st]
      if (!tbl) return ''
      const head = ann.periods.map((p) => `<th>${p.url
        ? `<a href="${esc(p.url)}" rel="noopener noreferrer">${esc(p.label)}</a>` : esc(p.label)}${
        p.hrk ? '<br /><small>preračunato iz HRK</small>' : ''}</th>`).join('')
      const body = tbl.rows.map((r) => `<tr>
        <td>${r.bold ? `<strong>${esc(r.label)}</strong>` : esc(r.label)}</td>
        ${ann.periods.map((p) => `<td>${finFmt(r.values[p.key], fin.unit)}</td>`).join('')}</tr>`).join('')
      return `<h2>${esc(tbl.label)} (godišnje, ${unitTxt})</h2>
        <table><thead><tr><th>Stavka</th>${head}</tr></thead><tbody>${body}</tbody></table>`
    }
    const body = `<main>
      <nav><a href="/">Naslovnica</a> › <a href="/dionica/${t}">${esc(company)}</a> › Financije</nav>
      <h1>Financijski izvještaji — ${esc(fin.name)}</h1>
      <p>As-reported financijski izvještaji (${esc(fin.name)}, ${esc(company)}):
      račun dobiti i gubitka, financijski položaj i novčani tok — svi periodi iz
      naše baze, ${unitTxt}. Stavke prema standardiziranoj shemi ekstrakcije;
      originalne oznake u izvornim dokumentima (poveznice u zaglavljima kolona).</p>
      ${tableFor('income')}${tableFor('balance')}${tableFor('cashflow')}
      <p><a href="/dionica/${t}">Profil dionice i ključni pokazatelji</a> ·
      <a href="/metodologija">Metodologija</a></p>
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`
    const canonicalEn = `${SITE}/en/stock/${t}/financials`
    const alternates = { hr: canonical, en: canonicalEn }
    await write(`dionica/${t}/financije`, page({
      title: `${company} financijski izvještaji — prihodi, dobit, bilanca | Burzovni list`,
      description: `Financijski izvještaji ${fin.name} (${company}): prihodi, dobit, bilanca i novčani tok po godinama — as-reported, s poveznicama na izvorne dokumente.`.slice(0, 155),
      canonical, body, alternates,
    }))
    urls.push({ loc: canonical, lastmod: eod, alt: alternates })

    // M38: engleska varijanta — stavke iz i18n rječnika (li.* ključevi)
    PRLOC = 'en-GB'
    const unitTxtEn = fin.unit === 'mil' ? tt('fin.unitMillions', 'en') : tt('fin.unitThousands', 'en')
    const stLblEn = { income: tt('fin.income', 'en'), balance: tt('fin.balance', 'en'),
      cashflow: tt('fin.cashflow', 'en') }
    const tableForEn = (st) => {
      const tbl = ann.statements[st]
      if (!tbl) return ''
      const head = ann.periods.map((p) => `<th>${p.url
        ? `<a href="${esc(p.url)}" rel="noopener noreferrer">${esc(p.label)}</a>` : esc(p.label)}${
        p.hrk ? `<br /><small>${esc(tt('fin.hrkBadge', 'en'))}</small>` : ''}</th>`).join('')
      const body2 = tbl.rows.map((r) => {
        const lbl = tt(`li.${r.item}`, 'en')
        return `<tr>
        <td>${r.bold ? `<strong>${esc(lbl)}</strong>` : esc(lbl)}</td>
        ${ann.periods.map((p) => `<td>${finFmt(r.values[p.key], fin.unit)}</td>`).join('')}</tr>`
      }).join('')
      return `<h2>${esc(stLblEn[st])} (annual, ${unitTxtEn})</h2>
        <table><thead><tr><th>${esc(tt('fin.item', 'en'))}</th>${head}</tr></thead><tbody>${body2}</tbody></table>`
    }
    const bodyEn = `<main>
      <nav><a href="/en">Home</a> › <a href="/en/stock/${t}">${esc(company)}</a> › Financials</nav>
      <h1>Financial statements — ${esc(fin.name)}</h1>
      <p>As-reported financial statements for ${esc(fin.name)} (${esc(company)}):
      income statement, balance sheet and cash flow — every period in our
      database, ${unitTxtEn}. Line items follow our standardized extraction
      schema; the original labels are in the source documents linked in the
      column headers.</p>
      ${tableForEn('income')}${tableForEn('balance')}${tableForEn('cashflow')}
      <p><a href="/en/stock/${t}">Stock profile and key indicators</a> ·
      <a href="/en/methodology">Methodology</a></p>
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`
    await write(`en/stock/${t}/financials`, page({
      title: `${company} financial statements — revenue, profit, balance sheet | Burzovni list`,
      description: `Financial statements of ${fin.name} (${company}): revenue, profit, balance sheet and cash flow by year — as reported, with links to source documents.`.slice(0, 155),
      canonical: canonicalEn, lang: 'en', alternates, body: bodyEn,
    }))
    urls.push({ loc: canonicalEn, lastmod: eod, alt: alternates })
    PRLOC = 'hr-HR'
    nFin += 1
  }
}

/* ---------- blog ---------- */
let posts = []
async function buildBlogPages() {
try {
  posts = JSON.parse(await fs.readFile(path.join(DIST, 'blog/index.json'), 'utf8'))
} catch { /* bez bloga */ }

/* M27: CMS postovi iz Supabase (SAMO status=published — RLS to i garantira
   za anon ključ). Markdown -> HTML uz ESCAPE sirovog HTML-a u izvoru
   (nikad neprovjereni HTML u stranicu), pa marked. Bez env ključeva build
   ostaje file-based (logirano). */
const SB_URL = process.env.VITE_SUPABASE_URL
const SB_KEY = process.env.VITE_SUPABASE_ANON_KEY
if (SB_URL && SB_KEY) {
  try {
    const { marked } = await import('marked')
    const r = await fetch(
      `${SB_URL}/rest/v1/blog_posts?status=eq.published`
      + `&select=slug,title,meta_description,content_md,tags,cover_image_url,published_at`
      + `&order=published_at.desc`,
      { headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` } })
    if (!r.ok) throw new Error(`REST ${r.status}`)
    const cms = await r.json()
    const seen = new Set(posts.map((p) => p.slug))
    for (const c of cms) {
      if (seen.has(c.slug)) continue // file-based post istog sluga ima prednost
      const safeMd = String(c.content_md).replace(/</g, '&lt;')
      const html = marked.parse(safeMd, { async: false })
      const entry = {
        slug: c.slug, title: c.title, category: 'Analize',
        date: (c.published_at || '').slice(0, 10),
        summary: c.meta_description || '',
        cover_image_url: c.cover_image_url || null,
      }
      await fs.writeFile(path.join(DIST, `blog/${c.slug}.json`),
        JSON.stringify({ ...entry, html }, null, 1))
      posts.push(entry)
    }
    posts.sort((a, b) => String(b.date).localeCompare(String(a.date)))
    await fs.writeFile(path.join(DIST, 'blog/index.json'), JSON.stringify(posts, null, 1))
    console.log(`[prerender] CMS blog: ${cms.length} objavljenih postova iz Supabase`)
  } catch (e) {
    console.log(`[prerender] CMS blog preskočen (${e.message}) — file-based postovi ostaju`)
  }
} else {
  console.log('[prerender] CMS blog preskočen — VITE_SUPABASE_URL/ANON_KEY nisu u build env')
}
for (const p of posts) {
  try {
    const post = JSON.parse(await fs.readFile(path.join(DIST, `blog/${p.slug}.json`), 'utf8'))
    const canonical = `${SITE}/blog/${p.slug}`
    await write(`blog/${p.slug}`, page({
      title: `${post.title} | Burzovni list`,
      description: (post.excerpt || post.title).slice(0, 155),
      canonical,
      ogType: 'article',
      published: post.date || null,
      body: `<main><h1>${esc(post.title)}</h1>${post.html || ''}</main>`,
    }))
    urls.push({ loc: canonical, lastmod: post.date || null })
  } catch { /* preskoči post bez JSON-a */ }
}
}

/* ---------- vijesti (M30) ---------- */
/* SAMO status='published' (RLS za anon ključ to i garantira). Zadano je
   vijest pokazivač na postojeću stranicu; detail /vijesti/<slug> se generira
   ISKLJUČIVO kad vijest ima body (izbjegavamo duplicate content). */
const kebab = (s) => String(s).toLowerCase().normalize('NFKD')
  .replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd')
  .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

let newsItems = []
{
  const nUrl = process.env.VITE_SUPABASE_URL
  const nKey = process.env.VITE_SUPABASE_ANON_KEY
  if (nUrl && nKey) {
    try {
      const r = await fetch(
        `${nUrl}/rest/v1/news_items?status=eq.published`
        + `&select=id,ticker,category,headline,body,link_path,published_at`
        + `&order=published_at.desc`,
        { headers: { apikey: nKey, Authorization: `Bearer ${nKey}` } })
      if (!r.ok) throw new Error(`REST ${r.status}`)
      const rows = await r.json()
      const seen = new Set()
      newsItems = rows.map((n) => {
        let slug = null
        if (n.body && String(n.body).trim()) {
          slug = kebab(n.headline) || n.id.slice(0, 8)
          if (seen.has(slug)) slug = `${slug}-${n.id.slice(0, 8)}`
          seen.add(slug)
        }
        return { ...n, slug }
      })
      console.log(`[prerender] vijesti: ${newsItems.length} objavljenih iz Supabase`)
    } catch (e) {
      console.log(`[prerender] vijesti preskočene (${e.message})`)
    }
  } else {
    console.log('[prerender] vijesti preskočene — VITE_SUPABASE_URL/ANON_KEY nisu u build env')
  }
}
await fs.mkdir(path.join(DIST, 'data'), { recursive: true })
await fs.writeFile(path.join(DIST, 'data/vijesti.json'), JSON.stringify(newsItems, null, 1))

async function buildNewsPages() {
  for (const n of newsItems.filter((x) => x.slug)) {
    const canonical = `${SITE}/vijesti/${n.slug}`
    const paras = String(n.body).split(/\n{2,}/).filter(Boolean)
      .map((par) => `<p>${esc(par)}</p>`).join('')
    await write(`vijesti/${n.slug}`, page({
      title: `${n.headline} | Burzovni list`,
      description: n.headline.slice(0, 155),
      canonical,
      ogType: 'article',
      published: n.published_at || null,
      body: `<main><h1>${esc(n.headline)}</h1>${paras}
        <p><a href="${esc(n.link_path)}">Pogledaj stranicu s podacima</a> · <a href="/vijesti">Sve vijesti</a></p></main>`,
    }))
    urls.push({ loc: canonical, lastmod: (n.published_at || '').slice(0, 10) || null })
  }
}

/* ---------- statičke stranice ---------- */
const FAQ = [ // MORA odgovarati sekciji "Česta pitanja" na /metodologija
  ['Što je fer-zona?', 'Raspon vrijednosti po dionici koji proizlazi iz naših metoda vrednovanja (sidrena metoda po arhetipu firme ± osjetljivost na ključne pretpostavke). Nije ciljna cijena — činjenični je prikaz što fundamenti govore uz javno ispisane pretpostavke.'],
  ['Kako se fer-zona računa?', 'Svaka firma dobiva arhetip (banka, industrija, holding…) koji određuje sidrenu metodu. Zona = sidro ± osjetljivost na ključnu pretpostavku; ostale metode služe kao potvrda. Svi parametri imaju citiran izvor na stranici dionice.'],
  ['Jesu li ovo preporuke za kupnju ili prodaju?', 'Ne. Servis ne objavljuje preporuke, rejtinge ni ciljne cijene. Cijena iznad ili ispod zone je činjenica iz podataka, ne signal — zaključak je uvijek čitateljev.'],
  ['Zašto neka dionica nema fer-zonu?', 'Zona se objavljuje samo kad podaci prođu validaciju. Ako izvješća nedostaju ili ne prođu provjere, prikazujemo samo tržišni profil — polja ostaju prazna (n/p).'],
  ['Koliko su podaci ažurni?', 'Cijene su službeni EOD zaključci Zagrebačke burze; ažuriraju se radnim danom nakon zatvaranja trgovine (16:00), a uz svaku cijenu stoji stvarni datum podatka. Financije se ažuriraju kad izdavatelj objavi izvješće (EHO registar).'],
]

/* ---------- M33: statične tablice (sadržajni temelj za crawlere; React se
   preko njih hidrira za sortiranje/filtriranje) ---------- */
const pct = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v)
  ? 'n/p' : `${num(v * 100, d)} %`)
const zoneStatus = (s, lang = 'hr') => {
  if (s.zone_low === null || s.zone_low === undefined || !s.price) return tt('common.na', lang)
  if (s.price > s.zone_high) {
    return `${num((s.price / s.zone_high - 1) * 100, 1)}${lang === 'en' ? '% above the fair-value zone' : ' % iznad fer-zone'}`
  }
  if (s.price < s.zone_low) {
    return `${num((1 - s.price / s.zone_low) * 100, 1)}${lang === 'en' ? '% below the fair-value zone' : ' % ispod fer-zone'}`
  }
  return tt('stock.inZone', lang)
}
const zoneTxt = (s, lang = 'hr') => (s.zone_low === null || s.zone_low === undefined
  ? tt('common.na', lang)
  : lang === 'en' ? `€${num(s.zone_low, 0)}–${num(s.zone_high, 0)}`
    : `${num(s.zone_low, 0)}–${num(s.zone_high, 0)} €`)

function screenerTable(lang = 'hr') {
  return withLang(lang, () => {
  const rows = overview.stocks.map((s) => `<tr>
    <td>${esc(s.ticker)}</td><td>${esc(s.name)}</td>
    <td>${s.price ? (lang === 'en' ? `€${num(s.price)}` : `${num(s.price)} €`) : tt('common.na', lang)}</td>
    <td>${zoneTxt(s, lang)}</td><td>${esc(zoneStatus(s, lang))}</td>
    <td>${esc(SEC(s.sector, lang))}</td></tr>`).join('')
  return `<table><thead><tr><th>${tt('common.ticker', lang)}</th><th>${tt('common.company', lang)}</th><th>${tt('common.price', lang)}</th>
    <th>${tt('stock.fairZone', lang)}</th><th>${tt('stock.priceVsZone', lang)}</th><th>${tt('common.sector', lang)}</th></tr></thead>
    <tbody>${rows}</tbody></table>`
  })
}

function usporedbaTable(lang = 'hr') {
  return withLang(lang, () => {
  const na = tt('common.na', lang)
  const rows = overview.stocks.map((s) => `<tr>
    <td>${esc(s.ticker)}</td><td>${esc(s.name)}</td>
    <td>${s.price ? (lang === 'en' ? `€${num(s.price)}` : `${num(s.price)} €`) : na}</td>
    <td>${num(s.pe, 1) ?? na}</td><td>${num(s.pb, 2) ?? na}</td>
    <td>${s.is_financial ? '—' : (num(s.ev_ebitda, 1) ?? na)}</td>
    <td>${pct(s.earnings_yield)}</td><td>${pct(s.div_yield)}</td>
    <td>${pct(s.payout, 0)}</td><td>${esc(zoneStatus(s, lang))}</td></tr>`).join('')
  return `<table><thead><tr><th>${tt('common.ticker', lang)}</th><th>${tt('common.company', lang)}</th><th>${tt('common.price', lang)}</th>
    <th>P/E</th><th>P/B</th><th>EV/EBITDA</th><th>Earnings yield</th>
    <th>${lang === 'en' ? 'Dividend yield' : 'Div. prinos'}</th><th>Payout</th><th>${tt('stock.priceVsZone', lang)}</th></tr></thead>
    <tbody>${rows}</tbody></table>`
  })
}

let dividendeData = { rows: [], as_of: null }
try {
  dividendeData = JSON.parse(await fs.readFile(path.join(DIST, 'data/dividende.json'), 'utf8'))
} catch { /* bez kalendara nema tablice */ }

/* ---------- M-IDX: indeksi ---------- */
let indeksiData = { indices: [], temperature: null }
try {
  indeksiData = JSON.parse(await fs.readFile(path.join(DIST, 'data/indeksi.json'), 'utf8'))
} catch { /* bez indeksa nema kartica */ }

const temperatureHtml = () => {
  const t = indeksiData.temperature
  if (!t || !t.total) return ''
  const p = (n) => Math.round((n / t.total) * 100)
  return `<h2>Temperatura tržišta</h2>
    <p>Sastavnice ${esc(t.index)}-a naspram naših fer-zona: <strong>${t.above} iznad zone (${p(t.above)} %)</strong>,
    ${t.inside} u zoni (${p(t.inside)} %), ${t.below} ispod zone (${p(t.below)} %)${t.np ? `, ${t.np} n/p` : ''}
    — od ukupno ${t.total} sastavnica. ${esc(t.note)}.</p>`
}

async function buildIndexPages() {
  for (const ix of indeksiData.indices) {
    const canonical = `${SITE}/indeks/${ix.slug}`
    const canonicalEn = `${SITE}/en/index/${ix.slug}`
    const alternates = { hr: canonical, en: canonicalEn }
    const pctTxt = (v) => (v === null || v === undefined ? 'n/p'
      : `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 2)} %`)
    const consRows = (ix.constituents || []).map((c) => `<tr>
      <td>${c.company
    ? `<a href="/dionica/${esc(c.company.toLowerCase())}">${esc(c.ticker)}</a>`
    : esc(c.ticker)}</td>
      <td>${esc(c.name || '')}</td>
      <td>${c.weight_pct !== null && c.weight_pct !== undefined ? `${num(c.weight_pct, 2)} %` : 'n/p'}</td></tr>`).join('')
    await write(`indeks/${ix.slug}`, page({
      title: `${ix.name} danas — vrijednost, sastav i povijest | Burzovni list`,
      description: `${ix.name} (${ix.description}): ${num(ix.value, 2)} (${ix.date}), dnevna promjena ${pctTxt(ix.change_pct)}, YTD ${pctTxt(ix.ytd_pct)}. Sastavnice s težinama i povijest.`.slice(0, 155),
      canonical, alternates,
      body: `<main>
        <nav><a href="/">Naslovnica</a> › <a href="/indeksi">Indeksi</a> › ${esc(ix.name)}</nav>
        <h1>${esc(ix.name)} — vrijednost, sastav i povijest</h1>
        <p>${esc(ix.description)}. Zadnja vrijednost: <strong>${num(ix.value, 2)}</strong>
        (službeni EOD za ${esc(ix.date)} · ažurira se nakon zatvaranja trgovine u 16:00).
        Dnevna promjena ${pctTxt(ix.change_pct)} · YTD ${pctTxt(ix.ytd_pct)} · 1 godina ${pctTxt(ix.y1_pct)}.</p>
        ${consRows ? `<h2>Sastavnice (${ix.constituents.length})</h2>
        <table><thead><tr><th>Ticker</th><th>Naziv</th><th>Težina</th></tr></thead>
        <tbody>${consRows}</tbody></table>
        <p>Izvor sastavnica i težina: ZSE (IndexComposition).</p>` : ''}
        <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
    }))
    PRLOC = 'en-GB'
    const pctTxtEn = (v) => (v === null || v === undefined ? 'n/a'
      : `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 2)}%`)
    await write(`en/index/${ix.slug}`, page({
      title: `${ix.name} today — value, constituents and history | Burzovni list`,
      description: `${ix.name}: ${num(ix.value, 2)} (${ix.date}), daily change ${pctTxtEn(ix.change_pct)}, YTD ${pctTxtEn(ix.ytd_pct)}. Zagreb Stock Exchange index with constituents and weights.`.slice(0, 155),
      canonical: canonicalEn, lang: 'en', alternates,
      body: `<main>
        <nav><a href="/en">Home</a> › <a href="/en/indices">Indices</a> › ${esc(ix.name)}</nav>
        <h1>${esc(ix.name)} — value, constituents and history</h1>
        <p>Last value: <strong>${num(ix.value, 2)}</strong>
        (official end-of-day value for ${esc(ix.date)} · updated after the 16:00 CET close).
        Daily change ${pctTxtEn(ix.change_pct)} · YTD ${pctTxtEn(ix.ytd_pct)} · 1 year ${pctTxtEn(ix.y1_pct)}.</p>
        ${(ix.constituents || []).length ? `<h2>Constituents (${ix.constituents.length})</h2>
        <table><thead><tr><th>Ticker</th><th>Name</th><th>Weight</th></tr></thead>
        <tbody>${ix.constituents.map((c) => `<tr>
          <td>${c.company ? `<a href="/en/stock/${esc(c.company.toLowerCase())}">${esc(c.ticker)}</a>` : esc(c.ticker)}</td>
          <td>${esc(c.name || '')}</td>
          <td>${c.weight_pct !== null && c.weight_pct !== undefined ? `${num(c.weight_pct, 2)}%` : 'n/a'}</td></tr>`).join('')}</tbody></table>
        <p>Source of constituents and weights: ZSE (IndexComposition).</p>` : ''}
        <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
    }))
    PRLOC = 'hr-HR'
    urls.push({ loc: canonical, lastmod: ix.date || eod, alt: alternates })
    urls.push({ loc: canonicalEn, lastmod: ix.date || eod, alt: alternates })
  }
}
function dividendeTable(lang = 'hr') {
  return withLang(lang, () => {
  const na = tt('common.na', lang)
  const rows = (dividendeData.rows || []).map((r) => `<tr>
    <td>${esc(r.class_ticker || r.company)}</td><td>${esc(r.name || r.company)}</td>
    <td>${r.fiscal_year ?? '—'}</td>
    <td>${r.amount_eur ? (lang === 'en' ? `€${num(r.amount_eur)}` : `${num(r.amount_eur)} €`) : na}</td>
    <td>${esc(r.ex_date || '—')}</td><td>${esc(r.payment_date || '—')}</td>
    <td>${esc(r.status || '—')}</td></tr>`).join('')
  return `<table><thead><tr><th>${tt('common.ticker', lang)}</th><th>${tt('common.company', lang)}</th><th>${tt('div.fy', lang)}</th>
    <th>${tt('div.amountPerShare', lang)}</th><th>${tt('div.exDate', lang)}</th><th>${tt('div.paymentDate', lang)}</th><th>${tt('common.status', lang)}</th></tr></thead>
    <tbody>${rows}</tbody></table>`
  })
}

/* ---------- M-BOND: obveznice ---------- */
let fondoviData = { units: [], mirex: [], synergy: [], units_available: false }
try {
  fondoviData = JSON.parse(await fs.readFile(path.join(DIST, 'data/fondovi.json'), 'utf8'))
} catch { /* bez podataka o fondovima */ }

let obveznice = { rows: [], as_of: null }
try {
  obveznice = JSON.parse(await fs.readFile(path.join(DIST, 'data/obveznice.json'), 'utf8'))
} catch { /* bez obveznica nema tablice */ }
const bondPct = (v, d = 2) => (v === null || v === undefined ? 'n/p' : `${num(v, d)} %`)

async function buildBondPages() {
  for (const r of obveznice.rows) {
    const sym = r.symbol.toLowerCase()
    const canonical = `${SITE}/obveznica/${sym}`
    const canonicalEn = `${SITE}/en/bond/${sym}`
    const alternates = { hr: canonical, en: canonicalEn }
    const schedRows = (r.schedule || []).map((c) => `<tr><td>${esc(c.date)}</td>
      <td>${num(c.amount_pct, 3)}</td><td>${c.amount_pct > 90 ? 'kupon + glavnica' : 'kupon'}</td></tr>`).join('')
    await write(`obveznica/${sym}`, page({
      title: `${r.symbol} obveznica — prinos (YTM), kupon i dospijeće | Burzovni list`,
      description: `${r.symbol} (${r.issuer || 'izdavatelj u obradi'}, ${r.btype}): kupon ${bondPct(r.coupon_pct, 3)}, dospijeće ${r.maturity_date || 'n/p'}, YTM ${bondPct(r.ytm_pct)}. Čista cijena u % nominale.`.slice(0, 155),
      canonical, alternates,
      body: `<main>
        <nav><a href="/">Naslovnica</a> › <a href="/obveznice">Obveznice</a> › ${esc(r.symbol)}</nav>
        <h1>${esc(r.symbol)} — ${esc(r.issuer || 'izdavatelj u obradi')} (${esc(r.btype)} obveznica)</h1>
        <p>${r.series_name ? `${esc(r.series_name)}. ` : ''}ISIN ${esc(r.isin)}.
        Kupon ${bondPct(r.coupon_pct, 3)} godišnje${r.freq_assumed ? ' (frekvencija: pretpostavka)' : ''} ·
        dospijeće ${esc(r.maturity_date || 'n/p')} · čista cijena
        ${r.price_pct !== null && r.price_pct !== undefined ? `${num(r.price_pct, 2)} % nominale (EOD ${esc(r.price_date)})` : 'n/p (nema trgovanja)'}${r.stale ? ' — indikativna (rijetko trgovanje)' : ''}.</p>
        <p>Prinos do dospijeća (YTM): <strong>${bondPct(r.ytm_pct)}</strong> ·
        tekući prinos ${bondPct(r.current_yield_pct)} ·
        modificirana duracija ${r.duration ? num(r.duration.modified, 2) : 'n/p'} ·
        obračunata kamata ${r.accrued_pct !== null && r.accrued_pct !== undefined ? num(r.accrued_pct, 3) : 'n/p'} % (${esc(r.day_count)}${r.day_count_assumed ? ', pretpostavka' : ''}).</p>
        ${schedRows ? `<h2>Raspored budućih isplata (na 100 nominale)</h2>
        <table><thead><tr><th>Datum</th><th>Iznos (% nominale)</th><th>Vrsta</th></tr></thead>
        <tbody>${schedRows}</tbody></table>` : ''}
        <p>Formule i konvencije: <a href="/metodologija">Metodologija — sekcija Obveznice</a>.</p>
        <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
    }))
    PRLOC = 'en-GB'
    await write(`en/bond/${sym}`, page({
      title: `${r.symbol} bond — yield to maturity (YTM), coupon and maturity | Burzovni list`,
      description: `${r.symbol} (${r.issuer || 'issuer in progress'}, ${r.btype}): coupon ${bondPct(r.coupon_pct, 3)}, maturity ${r.maturity_date || 'n/a'}, YTM ${bondPct(r.ytm_pct)}. Croatian bond, clean price in % of par.`.slice(0, 155),
      canonical: canonicalEn, lang: 'en', alternates,
      body: `<main>
        <nav><a href="/en">Home</a> › <a href="/en/bonds">Bonds</a> › ${esc(r.symbol)}</nav>
        <h1>${esc(r.symbol)} — ${esc(r.issuer || 'issuer in progress')} (${esc(r.btype)} bond)</h1>
        <p>${r.series_name ? `${esc(r.series_name)}. ` : ''}ISIN ${esc(r.isin)}.
        Coupon ${bondPct(r.coupon_pct, 3)} p.a.${r.freq_assumed ? ' (frequency: assumption)' : ''} ·
        maturity ${esc(r.maturity_date || 'n/a')} · clean price
        ${r.price_pct !== null && r.price_pct !== undefined ? `${num(r.price_pct, 2)}% of par (end-of-day ${esc(r.price_date)})` : 'n/a (no trading)'}${r.stale ? ' — indicative (infrequent trading)' : ''}.</p>
        <p>Yield to maturity (YTM): <strong>${bondPct(r.ytm_pct)}</strong> ·
        current yield ${bondPct(r.current_yield_pct)} ·
        modified duration ${r.duration ? num(r.duration.modified, 2) : 'n/a'} ·
        accrued interest ${r.accrued_pct !== null && r.accrued_pct !== undefined ? num(r.accrued_pct, 3) : 'n/a'}% (${esc(r.day_count)}${r.day_count_assumed ? ', assumption' : ''}).</p>
        <p>Formulas and conventions: <a href="/en/methodology">Methodology — Bonds section</a>.</p>
        <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
    }))
    PRLOC = 'hr-HR'
    urls.push({ loc: canonical, lastmod: r.price_date || obveznice.as_of || eod, alt: alternates })
    urls.push({ loc: canonicalEn, lastmod: r.price_date || obveznice.as_of || eod, alt: alternates })
  }
}

/* Dinamički body/extraHead za pojedine statičke rute — sve ostalo (naslov,
   opis, indexability) dolazi iz registryja. */
const BODY_BUILDERS = {
  '/': () => ({
    // M33: uz svaki ticker PUNO ime + cijena + odnos prema fer-zoni
    body: `<main><h1>Analiza dionica Zagrebačke burze</h1>
      <p>Fer vrijednost, CROBEX, dividende i pokazatelji za sve uvrštene dionice — službeni EOD podaci${eod ? ` (${esc(eod)})` : ''}.</p>
      ${temperatureHtml()}
      <h2>Dionice</h2><ul>${[...byCompany.entries()].map(([c, s]) => `<li><a href="/dionica/${c.toLowerCase()}">${esc(c)} — ${esc(s.name)}</a>${s.price ? ` · ${num(s.price)} €` : ''} · ${esc(zoneStatus(s))}</li>`).join('')}</ul>
      <p><a href="/usporedba">Usporedba dionica</a> · <a href="/dividende">Kalendar dividendi</a> · <a href="/metodologija">Metodologija</a> · <a href="/screener">Screener</a></p></main>`,
  }),
  '/screener': () => ({
    body: `<main><h1>Screener dionica Zagrebačke burze</h1>
      <p>Sve uvrštene dionice: cijena${eod ? ` (službeni EOD za ${esc(eod)})` : ''}, fer-zona iz javno opisane <a href="/metodologija">metodologije</a> i sektor. Sortiranje i filtriranje dostupni su u aplikaciji; podaci su isti.</p>
      ${screenerTable()}
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
  }),
  '/usporedba': () => ({
    body: `<main><h1>Usporedba dionica Zagrebačke burze</h1>
      <p>Multiplikatori svih uvrštenih dionica${eod ? ` (EOD za ${esc(eod)})` : ''}: P/E, P/B, EV/EBITDA, earnings yield, dividendni prinos, payout i položaj cijene naspram fer-zone. EV/EBITDA se ne prikazuje za financijski sektor (nije smislen).</p>
      ${usporedbaTable()}
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
  }),
  '/dividende': () => ({
    body: `<main><h1>Kalendar dividendi Zagrebačke burze</h1>
      <p>Iznosi po dionici, ex-datumi i datumi isplate iz službenih objava izdavatelja${dividendeData.as_of ? ` (stanje ${esc(dividendeData.as_of)})` : ''}. Derivirani povijesni zapisi nose oznaku izvora.</p>
      ${dividendeTable()}
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
  }),
  '/blog': () => ({
    // popis postova je učitan u buildBlogPages (registry: /blog/:slug ide prije)
    body: `<main><h1>Blog — edukacija o analizi dionica</h1>
      <ul>${posts.map((b) => `<li><a href="/blog/${esc(b.slug)}">${esc(b.title)}</a>${b.date ? ` (${esc(b.date)})` : ''}${b.summary ? ` — ${esc(b.summary)}` : ''}</li>`).join('')}</ul>
      <p><em>Edukativni sadržaj — nije investicijski savjet ni preporuka.</em></p></main>`,
  }),
  '/alati': () => ({
    body: `<main><h1>Alati i kalkulatori za ulagače</h1>
      <ul>
        <li>Kalkulator dividendnog prinosa — prinos iz iznosa dividende i cijene dionice.</li>
        <li>DCF/DDM kalkulator — sadašnja vrijednost novčanih tokova uz vlastite pretpostavke.</li>
        <li>Porez na kapitalnu dobit — hrvatska pravila s izvorima (rok držanja, stopa).</li>
        <li>Složeni kamatni račun — rast uloga kroz vrijeme.</li>
      </ul>
      <p>Kalkulatori rade u pregledniku (učitava se aplikacija) i ne spremaju unesene podatke.</p>
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
  }),
  '/indeksi': () => ({
    body: `<main><h1>Indeksi Zagrebačke burze</h1>
      <p>Službene vrijednosti svih ${indeksiData.indices.length} indeksa ZSE — ažuriraju se nakon zatvaranja trgovine (16:00).</p>
      ${temperatureHtml()}
      <table><thead><tr><th>Indeks</th><th>Vrijednost</th><th>Dan</th><th>YTD</th><th>1g</th></tr></thead>
      <tbody>${indeksiData.indices.map((ix) => {
    const pctTxt = (v) => (v === null || v === undefined ? 'n/p'
      : `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 2)} %`)
    return `<tr><td><a href="/indeks/${esc(ix.slug)}">${esc(ix.name)}</a> — ${esc(ix.description)}</td>
      <td>${num(ix.value, 2)}</td><td>${pctTxt(ix.change_pct)}</td>
      <td>${pctTxt(ix.ytd_pct)}</td><td>${pctTxt(ix.y1_pct)}</td></tr>`
  }).join('')}</tbody></table>
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
  }),
  '/obveznice': () => ({
    body: `<main><h1>Obveznice na Zagrebačkoj burzi — prinosi i dospijeća</h1>
      <p>Sve uvrštene obveznice: državne (uključujući narodne obveznice), municipalne i korporativne.
      Cijene su ČISTE, u % nominale${obveznice.as_of ? ` (zadnje trgovanje ${esc(obveznice.as_of)})` : ''};
      obveznicama se na ZSE trguje rijetko pa su cijene često indikativne.</p>
      <table><thead><tr><th>Oznaka</th><th>Izdavatelj</th><th>Tip</th><th>Dospijeće</th>
      <th>Kupon</th><th>Cijena (% nom.)</th><th>YTM</th><th>Mod. duracija</th></tr></thead>
      <tbody>${obveznice.rows.map((r) => `<tr>
        <td><a href="/obveznica/${esc(r.symbol.toLowerCase())}">${esc(r.symbol)}</a>${r.stale ? ' (ILIKV.)' : ''}</td>
        <td>${esc(r.issuer || 'master data u obradi')}</td><td>${esc(r.btype)}</td>
        <td>${esc(r.maturity_date || 'n/p')}</td><td>${bondPct(r.coupon_pct, 3)}</td>
        <td>${r.price_pct !== null && r.price_pct !== undefined ? num(r.price_pct, 2) : 'n/p'}</td>
        <td>${bondPct(r.ytm_pct)}</td>
        <td>${r.duration ? num(r.duration.modified, 2) : 'n/p'}</td></tr>`).join('')}</tbody></table>
      <p>Izračuni: <a href="/metodologija">Metodologija — sekcija Obveznice</a>.</p>
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
  }),
  '/mirovinski-fondovi': () => {
    const f = fondoviData
    const byT = new Map()
    for (const s of f.synergy || []) {
      if (!byT.has(s.ticker)) byT.set(s.ticker, { name: s.company_name, funds: [] })
      byT.get(s.ticker).funds.push(s)
    }
    return {
      body: `<main><h1>Mirovinski fondovi (OMF) — obračunske jedinice i prinosi</h1>
      <p>Obvezni mirovinski fondovi (AZ, Erste Plavi, PBZ CO, Raiffeisen; kategorije A/B/C)
      i Mirex za usporedbu. Izvor: HANFA javne objave, mjesečni ritam. Bez rangiranja —
      redoslijed je abecedni. ${f.units_available ? '' : 'Prvi mjesečni uvoz HANFA podataka još nije obavljen — vrijednosti jedinica pojavit će se nakon prve objave.'}</p>
      <h2>ZSE dionice s OMF-ovima među top 10 dioničara</h2>
      <table><thead><tr><th>Dionica</th><th>Fond (kategorija)</th><th>Ukupni udjel</th></tr></thead>
      <tbody>${[...byT.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([t, info]) => `<tr>
        <td><a href="/dionica/${esc(t.toLowerCase())}">${esc(t)}</a> — ${esc(info.name)}</td>
        <td>${esc(info.funds.map((x) => `${x.fund} (${x.category})`).join(', '))}</td>
        <td>${num(info.funds.reduce((a, x) => a + (x.pct || 0), 0), 2)} %</td></tr>`).join('')}</tbody></table>
      <p>Iz naših snapshota top 10 dioničara (ZSE/SKDD)${f.synergy?.[0]?.as_of ? `, stanje ${esc(f.synergy[0].as_of)}` : ''}.</p>
      <p><em>Činjenični prikaz, bez rangiranja i preporuka — nije investicijski savjet.</em></p></main>`,
    }
  },
  '/impressum': () => ({ body: `<main><h1>Impressum</h1>${renderStatic('/impressum')}</main>` }),
  '/uvjeti-koristenja': () => ({ body: `<main><h1>Uvjeti korištenja</h1>${renderStatic('/uvjeti-koristenja')}</main>` }),
  '/politika-privatnosti': () => ({ body: `<main><h1>Politika privatnosti</h1>${renderStatic('/politika-privatnosti')}</main>` }),
  '/politika-kolacica': () => ({ body: `<main><h1>Politika kolačića</h1>${renderStatic('/politika-kolacica')}</main>` }),
  '/metodologija': () => ({
    extraHead: jsonLd({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: FAQ.map(([q, a]) => ({
        '@type': 'Question', name: q,
        acceptedAnswer: { '@type': 'Answer', text: a },
      })),
    }),
    body: `<main><h1>Kako procjenjujemo</h1>${FAQ.map(([q, a]) => `<h2>${esc(q)}</h2><p>${esc(a)}</p>`).join('')}</main>`,
  }),
  '/vijesti': () => {
    const xh = String(process.env.VITE_X_HANDLE || '').replace(/^@/, '')
    return {
      body: `<main><h1>Vijesti</h1>
      <p>Kratke obavijesti o novim izvješćima, dividendama i ažuriranjima analiza.</p>
      ${xh ? `<p><a href="https://x.com/${esc(xh)}" rel="noopener noreferrer">Prati nas na X — @${esc(xh)}</a></p>` : ''}
      <ul>${newsItems.map((n) => `<li><a href="${n.slug ? `/vijesti/${n.slug}` : esc(n.link_path)}">${esc(n.headline)}</a>${n.published_at ? ` (${esc(n.published_at.slice(0, 10))})` : ''}</li>`).join('')}</ul>
      <p><em>Informativno — nije investicijski savjet ni preporuka.</em></p></main>`,
    }
  },
}


/* ---------- M38: EN body builderi za statičke rute (po EN putanji) ---------- */
const temperatureHtmlEn = () => {
  const t2 = indeksiData.temperature
  if (!t2 || !t2.total) return ''
  const p2 = (n) => Math.round((n / t2.total) * 100)
  return `<h2>Market temperature</h2>
    <p>${esc(t2.index)} constituents versus our fair-value zones: <strong>${t2.above} above the zone (${p2(t2.above)}%)</strong>,
    ${t2.inside} in the zone (${p2(t2.inside)}%), ${t2.below} below the zone (${p2(t2.below)}%)${t2.np ? `, ${t2.np} n/a` : ''}
    — out of ${t2.total} constituents.</p>`
}

const BODY_BUILDERS_EN = {
  '/en': () => ({
    body: `<main><h1>Zagreb Stock Exchange stock analysis</h1>
      <p>Fair value, CROBEX, dividends and key indicators for every listed Croatian stock — official end-of-day data${eod ? ` (${esc(eod)})` : ''}. Built for international investors: no paywall, every number carries its source.</p>
      ${temperatureHtmlEn()}
      <h2>Stocks</h2><ul>${[...byCompany.entries()].map(([c, s2]) => `<li><a href="/en/stock/${c.toLowerCase()}">${esc(c)} — ${esc(s2.name)}</a>${s2.price ? ` · €${num(s2.price)}` : ''} · ${esc(zoneStatus(s2, 'en'))}</li>`).join('')}</ul>
      <p><a href="/en/comparison">Compare stocks</a> · <a href="/en/dividends">Dividend calendar</a> · <a href="/en/methodology">Methodology</a> · <a href="/en/screener">Screener</a></p></main>`,
  }),
  '/en/screener': () => ({
    body: `<main><h1>Croatian stocks screener</h1>
      <p>Every listed Zagreb Stock Exchange stock: price${eod ? ` (official end-of-day close for ${esc(eod)})` : ''}, fair-value zone from our publicly described <a href="/en/methodology">methodology</a>, and sector. Sorting and filtering are available in the app; the data is identical.</p>
      ${screenerTable('en')}
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
  }),
  '/en/comparison': () => ({
    body: `<main><h1>Compare Zagreb Stock Exchange stocks</h1>
      <p>Multiples for every listed stock${eod ? ` (end-of-day close for ${esc(eod)})` : ''}: P/E, P/B, EV/EBITDA, earnings yield, dividend yield, payout and the position versus the fair-value zone. EV/EBITDA is not shown for financials (not meaningful).</p>
      ${usporedbaTable('en')}
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
  }),
  '/en/dividends': () => ({
    body: `<main><h1>ZSE dividend calendar</h1>
      <p>Amounts per share, ex-dates and payment dates from issuers' official filings${dividendeData.as_of ? ` (as of ${esc(dividendeData.as_of)})` : ''}. Derived historical records carry a source tag.</p>
      ${dividendeTable('en')}
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
  }),
  '/en/indices': () => ({
    body: `<main><h1>Zagreb Stock Exchange indices</h1>
      <p>Official values of all ${indeksiData.indices.length} ZSE indices — updated after the close of trading (16:00 CET).</p>
      ${temperatureHtmlEn()}
      <table><thead><tr><th>Index</th><th>Value</th><th>Day</th><th>YTD</th><th>1y</th></tr></thead>
      <tbody>${indeksiData.indices.map((ix) => {
    const pctTxt = (v) => (v === null || v === undefined ? 'n/a'
      : `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 2)}%`)
    return `<tr><td><a href="/en/index/${esc(ix.slug)}">${esc(ix.name)}</a></td>
      <td>${num(ix.value, 2)}</td><td>${pctTxt(ix.change_pct)}</td>
      <td>${pctTxt(ix.ytd_pct)}</td><td>${pctTxt(ix.y1_pct)}</td></tr>`
  }).join('')}</tbody></table>
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
  }),
  '/en/bonds': () => ({
    body: `<main><h1>Bonds on the Zagreb Stock Exchange — yields and maturities</h1>
      <p>Every listed bond: government (including Croatian retail bonds), municipal and corporate.
      Prices are CLEAN, in % of par${obveznice.as_of ? ` (last trade ${esc(obveznice.as_of)})` : ''};
      ZSE bonds trade rarely, so prices are often indicative.</p>
      <table><thead><tr><th>Symbol</th><th>Issuer</th><th>Type</th><th>Maturity</th>
      <th>Coupon</th><th>Price (% par)</th><th>YTM</th><th>Mod. duration</th></tr></thead>
      <tbody>${obveznice.rows.map((r) => `<tr>
        <td><a href="/en/bond/${esc(r.symbol.toLowerCase())}">${esc(r.symbol)}</a>${r.stale ? ' (ILLIQ.)' : ''}</td>
        <td>${esc(r.issuer || 'master data in progress')}</td><td>${esc(r.btype)}</td>
        <td>${esc(r.maturity_date || 'n/a')}</td><td>${bondPct(r.coupon_pct, 3)}</td>
        <td>${r.price_pct !== null && r.price_pct !== undefined ? num(r.price_pct, 2) : 'n/a'}</td>
        <td>${bondPct(r.ytm_pct)}</td>
        <td>${r.duration ? num(r.duration.modified, 2) : 'n/a'}</td></tr>`).join('')}</tbody></table>
      <p>Formulas and conventions: <a href="/en/methodology">Methodology — Bonds section</a>.</p>
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
  }),
  '/en/pension-funds': () => {
    const f = fondoviData
    const byT = new Map()
    for (const s2 of f.synergy || []) {
      if (!byT.has(s2.ticker)) byT.set(s2.ticker, { name: s2.company_name, funds: [] })
      byT.get(s2.ticker).funds.push(s2)
    }
    return {
      body: `<main><h1>Croatian mandatory pension funds — unit values and returns</h1>
      <p>Mandatory pension funds (AZ, Erste Plavi, PBZ CO, Raiffeisen; categories A/B/C)
      and the Mirex benchmark. Source: HANFA public releases, monthly cadence. No ranking —
      the order is alphabetical.</p>
      <h2>ZSE stocks with pension funds among the top-10 shareholders</h2>
      <table><thead><tr><th>Stock</th><th>Fund (category)</th><th>Total stake</th></tr></thead>
      <tbody>${[...byT.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([t2, info]) => `<tr>
        <td><a href="/en/stock/${esc(t2.toLowerCase())}">${esc(t2)}</a> — ${esc(info.name)}</td>
        <td>${esc(info.funds.map((x) => `${x.fund} (${x.category})`).join(', '))}</td>
        <td>${num(info.funds.reduce((a, x) => a + (x.pct || 0), 0), 2)}%</td></tr>`).join('')}</tbody></table>
      <p>From our top-10 shareholder snapshots (ZSE/SKDD).</p>
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
    }
  },
  '/en/methodology': () => {
    let metEn = null
    try {
      metEn = JSON.parse(fsSyncRead(path.join(DIST, 'data/metodologija_en.json')))
    } catch { /* bez EN metodologije nema bodyja */ }
    return {
      body: `<main><h1>${esc(metEn ? metEn.title : 'How we estimate value')}</h1>${metEn ? metEn.html : ''}</main>`,
    }
  },
  '/en/news': () => ({
    body: `<main><h1>News</h1>
      <p>Short notices about new financial reports, dividends and analysis updates on the Zagreb Stock Exchange — each links to the page with the underlying data and sources. News items are currently published in Croatian; every link leads to a bilingual data page.</p>
      <ul>${newsItems.map((n) => `<li><a href="${n.slug ? `/vijesti/${n.slug}` : esc(n.link_path)}">${esc(n.headline)}</a>${n.published_at ? ` (${esc(n.published_at.slice(0, 10))})` : ''}</li>`).join('')}</ul>
      <p><em>${esc(tt('common.notAdvice', 'en'))}</em></p></main>`,
  }),
  '/en/terms': () => ({ body: `<main><h1>Terms of Use</h1>${renderStatic('/en/terms')}</main>` }),
  '/en/privacy': () => ({ body: `<main><h1>Privacy Policy</h1>${renderStatic('/en/privacy')}</main>` }),
  '/en/cookies': () => ({ body: `<main><h1>Cookie Policy</h1>${renderStatic('/en/cookies')}</main>` }),
}

/* ---------- driver: registry je JEDINI popis ruta ---------- */
let nStatic = 0
for (const r of ROUTES) {
  if (r.prerender === false) continue // samo SPA fallback (admin, auth)
  if (r.expand === 'stocks') { await buildStockPages(); continue }
  if (r.expand === 'stocks_fin') { await buildFinPages(); continue }
  if (r.expand === 'blog') { await buildBlogPages(); continue }
  if (r.expand === 'news') { await buildNewsPages(); continue }
  if (r.expand === 'indices') { await buildIndexPages(); continue }
  if (r.expand === 'bonds') { await buildBondPages(); continue }
  const route = r.path.replace(/^\//, '')
  const canonical = route ? `${SITE}/${route}` : `${SITE}/`
  const canonicalEn = r.en ? `${SITE}${r.en.path}` : null
  const alternates = canonicalEn ? { hr: canonical, en: canonicalEn } : null
  const extra = BODY_BUILDERS[r.path] ? BODY_BUILDERS[r.path]() : {}
  const html = page({
    title: r.seo.title, description: r.seo.description, canonical,
    robots: r.indexable ? undefined : 'noindex', alternates, ...extra,
  })
  if (!route) await fs.writeFile(path.join(DIST, 'index.html'), html)
  else await write(route, html)
  // noindex rute NEMA u sitemapu upravo zato što nisu indexable u registryju
  if (r.indexable) urls.push({ loc: canonical, lastmod: eod, alt: alternates })
  nStatic += 1

  // M38: EN varijanta statičke rute (iz registryja — jedno mjesto za parove)
  if (r.en) {
    const enRoute = r.en.path.replace(/^\//, '')
    const extraEn = BODY_BUILDERS_EN[r.en.path] ? withLang('en', () => BODY_BUILDERS_EN[r.en.path]()) : {}
    const htmlEn = page({
      title: r.en.seo?.title || r.seo.title,
      description: r.en.seo?.description || r.seo.description,
      canonical: canonicalEn, lang: 'en', alternates,
      robots: r.indexable ? undefined : 'noindex', ...extraEn,
    })
    await write(enRoute, htmlEn)
    if (r.indexable) urls.push({ loc: canonicalEn, lastmod: eod, alt: alternates })
    nStatic += 1
  }
}

/* ---------- 404.html (pravi HTTP 404 umjesto soft-404) ----------
   Vercel za putanje bez odgovarajuće statičke datoteke (i bez rewritea)
   poslužuje dist/404.html sa STATUSOM 404 — nepostojeće rute (npr.
   /dionica/nepostojeca, /en) više ne vraćaju 200 sa SPA ljuskom.
   SPA fallback rewrite postoji SAMO za rute s prerender: false u
   registryju (auth/admin) — vidi frontend/vercel.json. */
await fs.writeFile(path.join(DIST, '404.html'), page({
  title: '404 — stranica nije pronađena | Burzovni list',
  description: 'Tražena stranica ne postoji. Pogledajte popis svih dionica ili naslovnicu.',
  canonical: `${SITE}/`,
  robots: 'noindex',
  body: `<main><h1>404 — stranica nije pronađena</h1>
    <p>Tražena adresa ne postoji ili je uklonjena.</p>
    <p><a href="/">Naslovnica</a> · <a href="/screener">Sve dionice</a> ·
    <a href="/dividende">Dividende</a> · <a href="/metodologija">Metodologija</a></p></main>`,
}))

/* ---------- sitemap ---------- */
const sm = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
${urls.map((u) => {
    const alt = u.alt
      ? `<xhtml:link rel="alternate" hreflang="hr" href="${u.alt.hr}" /><xhtml:link rel="alternate" hreflang="en" href="${u.alt.en}" /><xhtml:link rel="alternate" hreflang="x-default" href="${u.alt.hr}" />`
      : ''
    return `  <url><loc>${u.loc}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ''}${alt}</url>`
  }).join('\n')}
</urlset>
`
await fs.writeFile(path.join(DIST, 'sitemap.xml'), sm)

console.log(`[prerender] dionice=${nStocks}, financije=${nFin}, blog=${posts.length}, vijesti=${newsItems.length}, statične=${nStatic}, sitemap=${urls.length} URL-ova`)
