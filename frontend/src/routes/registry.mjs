/* JEDINI izvor istine za sve javne rute na sajtu.
   - router (src/main.jsx) gradi rute ISKLJUČIVO iz ovog popisa
   - prerender + sitemap (scripts/prerender.mjs) čitaju ISKLJUČIVO ovaj popis
   Nova stranica se dodaje OVDJE (+ komponenta u COMPONENTS mapi u main.jsx);
   nikad hardkodirana zasebno u routeru i zasebno u sitemap generatoru.
   Test tests/test_sitemap.py pada ako se ruta doda mimo registryja.

   Polja po ruti:
   - path        react-router putanja ('/dionica/:ticker' za dinamičke)
   - component   ime komponente — ključ u COMPONENTS mapi u main.jsx
   - indexable   true → ulazi u sitemap; false → noindex i NEMA ga u sitemapu
                 (nema zasebne exclude-liste — indexability živi samo ovdje)
   - seo         {title, description} za prerendane statičke stranice
   - expand      'stocks' | 'blog' | 'news' | 'indices' | 'bonds' — dinamička ruta
                 koju prerender širi po podacima (exporti dionica / postovi /
                 vijesti s bodyjem / indeksi)
   - prerender   false → stranica se NE prerendera (samo SPA fallback);
                 podrazumijevano true za statičke rute
   - en          M38: engleski par rute {path, seo} — JEDINO mjesto gdje se
                 definiraju HR↔EN parovi (router, prerender, sitemap,
                 hreflang i jezični switcher čitaju odavde). Ruta bez
                 'en' polja nema EN varijantu (blog, alati, admin...). */

export const ROUTES = [
  {
    path: '/',
    en: {
      path: '/en',
      seo: {
        title: 'Zagreb Stock Exchange stocks — prices, valuation, fair-value zones | Burzovni list',
        description: 'Fundamental analysis of Zagreb Stock Exchange (ZSE) stocks: prices, fair-value zones, key indicators, dividends and reports. Croatian stocks for international investors.',
      },
    },
    component: 'Trziste',
    indexable: true,
    seo: {
      title: 'Burzovni list — analiza dionica Zagrebačke burze',
      description: 'Fundamentalna analiza dionica Zagrebačke burze: cijene, fer-zone vrijednosti, pokazatelji, dividende i izvještaji. Informativno, nije investicijski savjet.',
    },
  },
  {
    path: '/screener',
    en: {
      path: '/en/screener',
      seo: {
        title: 'Croatian stocks screener — ZSE | Burzovni list',
        description: 'Screen all Zagreb Stock Exchange stocks: fair-value zone, P/E, P/B, dividend yield, turnover and sector — sortable and filterable.',
      },
    },
    component: 'Screener',
    indexable: true,
    seo: {
      title: 'Screener dionica ZSE | Burzovni list',
      description: 'Screener svih dionica Zagrebačke burze: fer-zona, P/E, P/B, prinos, promet i sektor — sortiranje i filtriranje.',
    },
  },
  {
    path: '/dionica/:ticker',
    en: { path: '/en/stock/:ticker' },
    component: 'StockPage',
    indexable: true,
    expand: 'stocks',
  },
  {
    path: '/dionica/:ticker/financije',
    en: { path: '/en/stock/:ticker/financials' },
    component: 'FinancijePage',
    indexable: true,
    expand: 'stocks_fin', // M37: as-reported izvještaji (data/fin/<T>.json)
  },
  {
    path: '/indeksi',
    en: {
      path: '/en/indices',
      seo: {
        title: 'Zagreb Stock Exchange indices — CROBEX, CROBEX10, CROBIS | Burzovni list',
        description: 'All Zagreb Stock Exchange indices in one place: values, daily and yearly changes, constituents with weights and market temperature versus fair-value zones.',
      },
    },
    component: 'IndeksiIndex',
    indexable: true,
    seo: {
      title: 'Indeksi Zagrebačke burze — CROBEX, CROBEX10, CROBIS | Burzovni list',
      description: 'Svi indeksi Zagrebačke burze na jednom mjestu: vrijednosti, dnevne i godišnje promjene, sastavnice s težinama i temperatura tržišta prema fer-zonama.',
    },
  },
  {
    path: '/indeks/:slug',
    en: { path: '/en/index/:slug' },
    component: 'IndeksDetail',
    indexable: true,
    expand: 'indices',
  },
  {
    path: '/obveznice',
    en: {
      path: '/en/bonds',
      seo: {
        title: 'Croatian bonds — ZSE yields (YTM) and maturities | Burzovni list',
        description: 'All bonds listed on the Zagreb Stock Exchange: government (retail), municipal and corporate — coupon, maturity, clean price, yield to maturity (YTM) and duration.',
      },
    },
    component: 'ObvezniceIndex',
    indexable: true,
    seo: {
      title: 'Obveznice ZSE — narodne obveznice, prinosi (YTM) i dospijeća | Burzovni list',
      description: 'Sve obveznice uvrštene na Zagrebačku burzu: državne (narodne), municipalne i korporativne — kupon, dospijeće, čista cijena, prinos do dospijeća (YTM) i duracija.',
    },
  },
  {
    path: '/obveznica/:symbol',
    en: { path: '/en/bond/:symbol' },
    component: 'ObveznicaDetail',
    indexable: true,
    expand: 'bonds',
  },
  {
    path: '/mirovinski-fondovi',
    en: {
      path: '/en/pension-funds',
      seo: {
        title: 'Croatian mandatory pension funds — unit values and returns | Burzovni list',
        description: 'Accounting unit values of Croatian mandatory pension funds (AZ, Erste Plavi, PBZ CO, Raiffeisen; categories A/B/C), the Mirex benchmark and ZSE stocks where the funds are top-10 shareholders.',
      },
    },
    component: 'MirovinskiFondovi',
    indexable: true,
    seo: {
      title: 'Mirovinski fondovi (OMF) — jedinice, prinosi i ZSE ulaganja | Burzovni list',
      description: 'Obračunske jedinice obveznih mirovinskih fondova (AZ, Erste Plavi, PBZ CO, Raiffeisen; kategorije A/B/C), Mirex za usporedbu i ZSE dionice u kojima se OMF-ovi pojavljuju među top 10 dioničara.',
    },
  },
  {
    path: '/mirovinski-fond/:slug',
    en: { path: '/en/pension-fund/:slug' },
    component: 'FondDetail',
    indexable: true,
    expand: 'funds', // zasebna stranica po fondu (obitelj+kategorija)
  },
  {
    path: '/usporedba',
    en: {
      path: '/en/comparison',
      seo: {
        title: 'Compare Zagreb Stock Exchange stocks — P/E, P/B, dividend yield | Burzovni list',
        description: 'Compare all ZSE stocks: P/E, P/B, EV/EBITDA, earnings yield, dividend yield, payout and gap to fair-value zone — sorting, filters, up to 5 stocks side by side.',
      },
    },
    component: 'Usporedba',
    indexable: true,
    seo: {
      title: 'Usporedba dionica Zagrebačke burze — P/E, P/B, dividendni prinos | Burzovni list',
      description: 'Usporedite sve dionice ZSE: P/E, P/B, EV/EBITDA, earnings yield, dividendni prinos, payout i raskorak od fer-zone — sortiranje, filtri i usporedba do 5 dionica.',
    },
  },
  {
    path: '/dividende',
    en: {
      path: '/en/dividends',
      seo: {
        title: 'ZSE dividend calendar — ex-dates, payments and yields | Burzovni list',
        description: 'Zagreb Stock Exchange dividend calendar: amounts per share, ex-dates, payment dates and dividend yields for all companies. From official filings, updated daily.',
      },
    },
    component: 'Dividende',
    indexable: true,
    seo: {
      title: 'Kalendar dividendi ZSE — ex-datumi, isplate i prinosi | Burzovni list',
      description: 'Kalendar dividendi Zagrebačke burze: iznosi, ex-datumi, datumi isplate i dividendni prinosi svih firmi. Iz službenih objava, dnevno ažurirano.',
    },
  },
  {
    path: '/metodologija',
    en: {
      path: '/en/methodology',
      seo: {
        title: 'Methodology — how we estimate value | Burzovni list',
        description: 'How we compute fair-value zones for Croatian stocks: methods by company archetype, data sources, parameters with citations. No recommendations — by design.',
      },
    },
    component: 'Metodologija',
    indexable: true,
    seo: {
      title: 'Metodologija — kako procjenjujemo | Burzovni list',
      description: 'Kako računamo fer-zone: metode po arhetipu firme, izvori podataka, parametri s citatima i priznate greške. Bez preporuka — po dizajnu.',
    },
  },
  {
    path: '/blog/:slug',
    component: 'BlogPost',
    indexable: true,
    expand: 'blog',
  },
  {
    path: '/blog',
    component: 'BlogIndex',
    indexable: true,
    seo: {
      title: 'Blog — edukacija o analizi dionica | Burzovni list',
      description: 'Edukativni tekstovi: kako čitati P/E, što je fer-zona, zašto holding ne vrijedi kao zbroj dijelova — bez preporuka.',
    },
  },
  {
    path: '/vijesti',
    en: {
      path: '/en/news',
      seo: {
        title: 'ZSE news — new reports, dividends and updates | Burzovni list',
        description: 'Short news from the Zagreb Stock Exchange: new financial reports, announced dividends and analysis updates — each links to the page with data and sources.',
      },
    },
    component: 'VijestiIndex',
    indexable: true,
    seo: {
      title: 'Vijesti — nova izvješća, dividende i ažuriranja | Burzovni list',
      description: 'Kratke vijesti sa Zagrebačke burze: nova financijska izvješća, najavljene dividende i ažuriranja analiza — svaka vodi na stranicu s podacima i izvorima.',
    },
  },
  {
    path: '/vijesti/:slug',
    component: 'VijestDetail',
    indexable: true,
    expand: 'news', // detail stranica postoji SAMO za vijesti s bodyjem
  },
  {
    path: '/alati',
    component: 'Alati',
    indexable: true,
    seo: {
      title: 'Alati i kalkulatori za ulagače | Burzovni list',
      description: 'Kalkulatori: dividendni prinos, DCF/DDM, porez na kapitalnu dobit (HR pravila s izvorima), složeni kamatni račun.',
    },
  },
  {
    path: '/impressum',
    component: 'Impressum',
    indexable: true,
    seo: {
      title: 'Impressum | Burzovni list',
      description: 'Impressum servisa Burzovni list — informativna analitička platforma za dionice Zagrebačke burze.',
    },
  },
  {
    path: '/uvjeti-koristenja',
    en: {
      path: '/en/terms',
      seo: {
        title: 'Terms of Use | Burzovni list',
        description: 'Terms of Use of Burzovni list: informational nature of the content, accounts, intellectual property, liability. In case of dispute, the Croatian version prevails.',
      },
    },
    component: 'UvjetiKoristenja',
    indexable: true,
    seo: {
      title: 'Uvjeti korištenja | Burzovni list',
      description: 'Uvjeti korištenja servisa Burzovni list: informativna priroda sadržaja, računi, intelektualno vlasništvo, odgovornost.',
    },
  },
  {
    path: '/politika-privatnosti',
    en: {
      path: '/en/privacy',
      seo: {
        title: 'Privacy Policy | Burzovni list',
        description: 'Privacy Policy: what data we process, legal bases, processors, retention periods and your GDPR rights. In case of dispute, the Croatian version prevails.',
      },
    },
    component: 'PolitikaPrivatnosti',
    indexable: true,
    seo: {
      title: 'Politika privatnosti | Burzovni list',
      description: 'Politika privatnosti: koje podatke obrađujemo, pravne osnove, obrađivači, rokovi čuvanja i vaša prava (GDPR).',
    },
  },
  {
    path: '/politika-kolacica',
    en: {
      path: '/en/cookies',
      seo: {
        title: 'Cookie Policy | Burzovni list',
        description: 'Cookie Policy: table of cookies and local storage, consent management, legal basis. In case of dispute, the Croatian version prevails.',
      },
    },
    component: 'PolitikaKolacica',
    indexable: true,
    seo: {
      title: 'Politika kolačića | Burzovni list',
      description: 'Politika kolačića: tablica kolačića i lokalne pohrane, upravljanje pristankom, pravna osnova.',
    },
  },
  {
    path: '/portfelj',
    component: 'Portfelj',
    indexable: false, // privatna stranica: noindex + nema je u sitemapu
    seo: {
      title: 'Portfelj | Burzovni list',
      description: 'Moj portfelj — evidencija pozicija uz naše analize.',
    },
  },
  {
    path: '/auth/callback',
    component: 'AuthCallback',
    indexable: false,
    prerender: false, // samo SPA fallback (OAuth povratna ruta)
  },
  {
    path: '/admin',
    component: 'Admin',
    indexable: false,
    prerender: false, // samo SPA fallback; komponenta sama postavlja noindex
  },
]

/* ---------- M38: HR↔EN mapiranje putanja (switcher + hreflang) ---------- */
const _toRe = (pattern) => new RegExp(
  `^${pattern.replace(/[.*+?^${}()|[\]\\]/g, (c) => (c === ':' ? c : `\\${c}`))
    .replace(/:([A-Za-z]+)/g, '(?<$1>[^/]+)')}$`)

const _fill = (pattern, params) =>
  pattern.replace(/:([A-Za-z]+)/g, (_, name) => params[name] || '')

/* pairPath('/dionica/koei') -> '/en/stock/koei'; pairPath('/en/screener')
   -> '/screener'; ruta bez para -> null (switcher tada vodi na home). */
export function pairPath(pathname) {
  for (const r of ROUTES) {
    if (!r.en) continue
    let m = pathname.match(_toRe(r.path))
    if (m) return _fill(r.en.path, m.groups || {})
    m = pathname.match(_toRe(r.en.path))
    if (m) return _fill(r.path, m.groups || {})
  }
  return null
}
