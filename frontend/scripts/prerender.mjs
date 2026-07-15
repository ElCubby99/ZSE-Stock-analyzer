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
import path from 'node:path'
import { ROUTES } from '../src/routes/registry.mjs'

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

  await write(`dionica/${t}`, page({
    title: `${company} dionica — ${name} | cijena, analiza vrijednosti, fer-zona | Burzovni list`,
    description, canonical, extraHead: bc, body,
  }))
  urls.push({ loc: canonical, lastmod: s.date || eod })
  nStocks += 1
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

/* Dinamički body/extraHead za pojedine statičke rute — sve ostalo (naslov,
   opis, indexability) dolazi iz registryja. */
const BODY_BUILDERS = {
  '/': () => ({
    body: `<main><h1>Analiza dionica Zagrebačke burze</h1>
      <p>Fer vrijednost, CROBEX, dividende i pokazatelji za sve uvrštene dionice — službeni EOD podaci${eod ? ` (${esc(eod)})` : ''}.</p>
      <h2>Dionice</h2><ul>${[...byCompany.keys()].map((c) => `<li><a href="/dionica/${c.toLowerCase()}">${esc(c)}</a></li>`).join('')}</ul>
      <p><a href="/usporedba">Usporedba dionica</a> · <a href="/dividende">Kalendar dividendi</a> · <a href="/metodologija">Metodologija</a> · <a href="/screener">Screener</a></p></main>`,
  }),
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

/* ---------- driver: registry je JEDINI popis ruta ---------- */
let nStatic = 0
for (const r of ROUTES) {
  if (r.prerender === false) continue // samo SPA fallback (admin, auth)
  if (r.expand === 'stocks') { await buildStockPages(); continue }
  if (r.expand === 'blog') { await buildBlogPages(); continue }
  if (r.expand === 'news') { await buildNewsPages(); continue }
  const route = r.path.replace(/^\//, '')
  const canonical = route ? `${SITE}/${route}` : `${SITE}/`
  const extra = BODY_BUILDERS[r.path] ? BODY_BUILDERS[r.path]() : {}
  const html = page({
    title: r.seo.title, description: r.seo.description, canonical,
    robots: r.indexable ? undefined : 'noindex', ...extra,
  })
  if (!route) await fs.writeFile(path.join(DIST, 'index.html'), html)
  else await write(route, html)
  // noindex rute NEMA u sitemapu upravo zato što nisu indexable u registryju
  if (r.indexable) urls.push({ loc: canonical, lastmod: eod })
  nStatic += 1
}

/* ---------- sitemap ---------- */
const sm = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url><loc>${u.loc}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ''}</url>`).join('\n')}
</urlset>
`
await fs.writeFile(path.join(DIST, 'sitemap.xml'), sm)

console.log(`[prerender] dionice=${nStocks}, blog=${posts.length}, vijesti=${newsItems.length}, statične=${nStatic}, sitemap=${urls.length} URL-ova`)
