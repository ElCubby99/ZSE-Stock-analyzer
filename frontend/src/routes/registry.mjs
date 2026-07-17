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
                 podrazumijevano true za statičke rute */

export const ROUTES = [
  {
    path: '/',
    component: 'Trziste',
    indexable: true,
    seo: {
      title: 'Burzovni list — analiza dionica Zagrebačke burze',
      description: 'Fundamentalna analiza dionica Zagrebačke burze: cijene, fer-zone vrijednosti, pokazatelji, dividende i izvještaji. Informativno, nije investicijski savjet.',
    },
  },
  {
    path: '/screener',
    component: 'Screener',
    indexable: true,
    seo: {
      title: 'Screener dionica ZSE | Burzovni list',
      description: 'Screener svih dionica Zagrebačke burze: fer-zona, P/E, P/B, prinos, promet i sektor — sortiranje i filtriranje.',
    },
  },
  {
    path: '/dionica/:ticker',
    component: 'StockPage',
    indexable: true,
    expand: 'stocks',
  },
  {
    path: '/dionica/:ticker/financije',
    component: 'FinancijePage',
    indexable: true,
    expand: 'stocks_fin', // M37: as-reported izvještaji (data/fin/<T>.json)
  },
  {
    path: '/indeksi',
    component: 'IndeksiIndex',
    indexable: true,
    seo: {
      title: 'Indeksi Zagrebačke burze — CROBEX, CROBEX10, CROBIS | Burzovni list',
      description: 'Svi indeksi Zagrebačke burze na jednom mjestu: vrijednosti, dnevne i godišnje promjene, sastavnice s težinama i temperatura tržišta prema fer-zonama.',
    },
  },
  {
    path: '/indeks/:slug',
    component: 'IndeksDetail',
    indexable: true,
    expand: 'indices',
  },
  {
    path: '/obveznice',
    component: 'ObvezniceIndex',
    indexable: true,
    seo: {
      title: 'Obveznice ZSE — narodne obveznice, prinosi (YTM) i dospijeća | Burzovni list',
      description: 'Sve obveznice uvrštene na Zagrebačku burzu: državne (narodne), municipalne i korporativne — kupon, dospijeće, čista cijena, prinos do dospijeća (YTM) i duracija.',
    },
  },
  {
    path: '/obveznica/:symbol',
    component: 'ObveznicaDetail',
    indexable: true,
    expand: 'bonds',
  },
  {
    path: '/mirovinski-fondovi',
    component: 'MirovinskiFondovi',
    indexable: true,
    seo: {
      title: 'Mirovinski fondovi (OMF) — jedinice, prinosi i ZSE ulaganja | Burzovni list',
      description: 'Obračunske jedinice obveznih mirovinskih fondova (AZ, Erste Plavi, PBZ CO, Raiffeisen; kategorije A/B/C), Mirex za usporedbu i ZSE dionice u kojima se OMF-ovi pojavljuju među top 10 dioničara.',
    },
  },
  {
    path: '/usporedba',
    component: 'Usporedba',
    indexable: true,
    seo: {
      title: 'Usporedba dionica Zagrebačke burze — P/E, P/B, dividendni prinos | Burzovni list',
      description: 'Usporedite sve dionice ZSE: P/E, P/B, EV/EBITDA, earnings yield, dividendni prinos, payout i raskorak od fer-zone — sortiranje, filtri i usporedba do 5 dionica.',
    },
  },
  {
    path: '/dividende',
    component: 'Dividende',
    indexable: true,
    seo: {
      title: 'Kalendar dividendi ZSE — ex-datumi, isplate i prinosi | Burzovni list',
      description: 'Kalendar dividendi Zagrebačke burze: iznosi, ex-datumi, datumi isplate i dividendni prinosi svih firmi. Iz službenih objava, dnevno ažurirano.',
    },
  },
  {
    path: '/metodologija',
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
    component: 'UvjetiKoristenja',
    indexable: true,
    seo: {
      title: 'Uvjeti korištenja | Burzovni list',
      description: 'Uvjeti korištenja servisa Burzovni list: informativna priroda sadržaja, računi, intelektualno vlasništvo, odgovornost.',
    },
  },
  {
    path: '/politika-privatnosti',
    component: 'PolitikaPrivatnosti',
    indexable: true,
    seo: {
      title: 'Politika privatnosti | Burzovni list',
      description: 'Politika privatnosti: koje podatke obrađujemo, pravne osnove, obrađivači, rokovi čuvanja i vaša prava (GDPR).',
    },
  },
  {
    path: '/politika-kolacica',
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
