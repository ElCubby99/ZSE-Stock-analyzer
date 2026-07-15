/* M25 DIO 2: prerender / SSG-light — pokreće se NAKON `vite build`.
   Za svaku dionicu, blog post i statičku stranicu generira vlastiti
   dist/<ruta>/index.html s: <title>, meta description, canonical, OG/Twitter,
   JSON-LD (BreadcrumbList / FAQPage) i STATIČKIM sadržajem u #root (botovi i
   curl vide ime firme, cijenu i fer-zonu bez izvršavanja JS-a; React na
   hydrateu zamijeni sadržaj). Regenerira i sitemap.xml s lastmod = EOD datum.

   Ovo je svjesno "manja opcija" umjesto migracije na Next.js/vite-ssg:
   nula novih ovisnosti, build ostaje isti, sav sadržaj dolazi iz istih
   statičkih JSON exporta koje SPA ionako koristi. */
import { promises as fs } from 'node:fs'
import path from 'node:path'

const DIST = path.resolve(process.cwd(), 'dist')
const SITE = 'https://burzovnilist.com'

const template = await fs.readFile(path.join(DIST, 'index.html'), 'utf8')
const overview = JSON.parse(await fs.readFile(path.join(DIST, 'data/overview.json'), 'utf8'))

const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const num = (v, d = 2) => (v === null || v === undefined || Number.isNaN(v)
  ? null
  : Number(v).toLocaleString('hr-HR', { minimumFractionDigits: d, maximumFractionDigits: d }))

function page({ title, description, canonical, robots, extraHead = '', body = '' }) {
  let html = template
  html = html.replace(/<title>[\s\S]*?<\/title>/, `<title>${esc(title)}</title>`)
  html = html.replace(/<meta name="description" content="[^"]*" \/>/,
    `<meta name="description" content="${esc(description)}" />`)
  const head = [
    `<link rel="canonical" href="${canonical}" />`,
    robots ? `<meta name="robots" content="${robots}" />` : '',
    `<meta property="og:type" content="website" />`,
    `<meta property="og:site_name" content="Burzovni list" />`,
    `<meta property="og:title" content="${esc(title)}" />`,
    `<meta property="og:description" content="${esc(description)}" />`,
    `<meta property="og:url" content="${canonical}" />`,
    `<meta property="og:image" content="${SITE}/og-default.png" />`,
    `<meta property="og:locale" content="hr_HR" />`,
    `<meta name="twitter:card" content="summary_large_image" />`,
    `<meta name="twitter:title" content="${esc(title)}" />`,
    `<meta name="twitter:description" content="${esc(description)}" />`,
    `<meta name="twitter:image" content="${SITE}/og-default.png" />`,
    extraHead,
  ].filter(Boolean).join('\n  ')
  html = html.replace('</head>', `  ${head}\n</head>`)
  // statički sadržaj u #root — React ga na mountu zamijeni
  html = html.replace('<div id="root"></div>', `<div id="root">${body}</div>`)
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
      <p>${price ? `Zadnja cijena: <strong>${price} €</strong>${s.date ? ` (službeni EOD ${esc(s.date)}, dan zaostatka)` : ''}.` : 'Cijena trenutno nije dostupna.'}</p>
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

  await write(`dionica/${t}`, page({
    title: `${company} dionica — ${name} | cijena, analiza vrijednosti, fer-zona | Burzovni list`,
    description, canonical, extraHead: bc, body,
  }))
  urls.push({ loc: canonical, lastmod: s.date || eod })
  nStocks += 1
}

/* ---------- blog ---------- */
let posts = []
try {
  posts = JSON.parse(await fs.readFile(path.join(DIST, 'blog/index.json'), 'utf8'))
} catch { /* bez bloga */ }
for (const p of posts) {
  try {
    const post = JSON.parse(await fs.readFile(path.join(DIST, `blog/${p.slug}.json`), 'utf8'))
    const canonical = `${SITE}/blog/${p.slug}`
    await write(`blog/${p.slug}`, page({
      title: `${post.title} | Burzovni list`,
      description: (post.excerpt || post.title).slice(0, 155),
      canonical,
      body: `<main><h1>${esc(post.title)}</h1>${post.html || ''}</main>`,
    }))
    urls.push({ loc: canonical, lastmod: post.date || null })
  } catch { /* preskoči post bez JSON-a */ }
}

/* ---------- statičke stranice ---------- */
const FAQ = [ // MORA odgovarati sekciji "Česta pitanja" na /metodologija
  ['Što je fer-zona?', 'Raspon vrijednosti po dionici koji proizlazi iz naših metoda vrednovanja (sidrena metoda po arhetipu firme ± osjetljivost na ključne pretpostavke). Nije ciljna cijena — činjenični je prikaz što fundamenti govore uz javno ispisane pretpostavke.'],
  ['Kako se fer-zona računa?', 'Svaka firma dobiva arhetip (banka, industrija, holding…) koji određuje sidrenu metodu. Zona = sidro ± osjetljivost na ključnu pretpostavku; ostale metode služe kao potvrda. Svi parametri imaju citiran izvor na stranici dionice.'],
  ['Jesu li ovo preporuke za kupnju ili prodaju?', 'Ne. Servis ne objavljuje preporuke, rejtinge ni ciljne cijene. Cijena iznad ili ispod zone je činjenica iz podataka, ne signal — zaključak je uvijek čitateljev.'],
  ['Zašto neka dionica nema fer-zonu?', 'Zona se objavljuje samo kad podaci prođu validaciju. Ako izvješća nedostaju ili ne prođu provjere, prikazujemo samo tržišni profil — polja ostaju prazna (n/p).'],
  ['Koliko su podaci ažurni?', 'Cijene su službeni EOD zaključci Zagrebačke burze s danom zaostatka; financije se ažuriraju kad izdavatelj objavi izvješće (EHO registar).'],
]

const staticPages = [
  { route: '', title: 'Burzovni list — analiza dionica Zagrebačke burze',
    description: 'Fundamentalna analiza dionica Zagrebačke burze: cijene, fer-zone vrijednosti, pokazatelji, dividende i izvještaji. Informativno, nije investicijski savjet.',
    body: `<main><h1>Analiza dionica Zagrebačke burze</h1>
      <p>Fer vrijednost, CROBEX, dividende i pokazatelji za sve uvrštene dionice — službeni EOD podaci${eod ? ` (${esc(eod)})` : ''}.</p>
      <h2>Dionice</h2><ul>${[...byCompany.keys()].map((c) => `<li><a href="/dionica/${c.toLowerCase()}">${esc(c)}</a></li>`).join('')}</ul>
      <p><a href="/dividende">Kalendar dividendi</a> · <a href="/metodologija">Metodologija</a> · <a href="/screener">Screener</a></p></main>` },
  { route: 'dividende', title: 'Kalendar dividendi ZSE — ex-datumi, isplate i prinosi | Burzovni list',
    description: 'Kalendar dividendi Zagrebačke burze: iznosi, ex-datumi, datumi isplate i dividendni prinosi svih firmi. Iz službenih objava, dnevno ažurirano.' },
  { route: 'screener', title: 'Screener dionica ZSE | Burzovni list',
    description: 'Screener svih dionica Zagrebačke burze: fer-zona, P/E, P/B, prinos, promet i sektor — sortiranje i filtriranje.' },
  { route: 'metodologija', title: 'Metodologija — kako procjenjujemo | Burzovni list',
    description: 'Kako računamo fer-zone: metode po arhetipu firme, izvori podataka, parametri s citatima i priznate greške. Bez preporuka — po dizajnu.',
    extraHead: jsonLd({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: FAQ.map(([q, a]) => ({
        '@type': 'Question', name: q,
        acceptedAnswer: { '@type': 'Answer', text: a },
      })),
    }),
    body: `<main><h1>Kako procjenjujemo</h1>${FAQ.map(([q, a]) => `<h2>${esc(q)}</h2><p>${esc(a)}</p>`).join('')}</main>` },
  { route: 'blog', title: 'Blog — edukacija o analizi dionica | Burzovni list',
    description: 'Edukativni tekstovi: kako čitati P/E, što je fer-zona, zašto holding ne vrijedi kao zbroj dijelova — bez preporuka.' },
  { route: 'alati', title: 'Alati i kalkulatori za ulagače | Burzovni list',
    description: 'Kalkulatori: dividendni prinos, DCF/DDM, porez na kapitalnu dobit (HR pravila s izvorima), složeni kamatni račun.' },
  { route: 'impressum', title: 'Impressum | Burzovni list',
    description: 'Impressum servisa Burzovni list — informativna analitička platforma za dionice Zagrebačke burze.' },
  { route: 'uvjeti-koristenja', title: 'Uvjeti korištenja | Burzovni list',
    description: 'Uvjeti korištenja servisa Burzovni list: informativna priroda sadržaja, računi, intelektualno vlasništvo, odgovornost.' },
  { route: 'politika-privatnosti', title: 'Politika privatnosti | Burzovni list',
    description: 'Politika privatnosti: koje podatke obrađujemo, pravne osnove, obrađivači, rokovi čuvanja i vaša prava (GDPR).' },
  { route: 'politika-kolacica', title: 'Politika kolačića | Burzovni list',
    description: 'Politika kolačića: tablica kolačića i lokalne pohrane, upravljanje pristankom, pravna osnova.' },
  { route: 'portfelj', title: 'Portfelj | Burzovni list',
    description: 'Moj portfelj — evidencija pozicija uz naše analize.', robots: 'noindex' },
]

for (const p of staticPages) {
  const canonical = `${SITE}/${p.route}`.replace(/\/$/, '') || SITE
  const html = page({ ...p, canonical: p.route ? canonical : `${SITE}/` })
  if (p.route === '') await fs.writeFile(path.join(DIST, 'index.html'), html)
  else await write(p.route, html)
  if (!p.robots) urls.push({ loc: p.route ? canonical : `${SITE}/`, lastmod: eod })
}

/* ---------- sitemap ---------- */
const sm = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url><loc>${u.loc}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ''}</url>`).join('\n')}
</urlset>
`
await fs.writeFile(path.join(DIST, 'sitemap.xml'), sm)

console.log(`[prerender] dionice=${nStocks}, blog=${posts.length}, statične=${staticPages.length}, sitemap=${urls.length} URL-ova`)
