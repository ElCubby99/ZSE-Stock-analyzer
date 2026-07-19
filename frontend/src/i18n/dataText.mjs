/* M38: prijevod PODATKOVNIH tekstova koje generira Python backend
   (indicators why/formula/np_reason/basis, global peers, news note…).
   Brojke ostaju u istim slotovima; prevodi se samo okolni tekst
   (nalog M38 DIO 1.2). Exact-match mapa + pattern pravila za stringove
   s dinamičkim dijelovima (datumi, n=, popisi peera).

   tx(s, 'en') vraća EN prijevod; nepoznat string prolazi kroz pattern
   pravila, a ako i dalje sadrži hrvatski tekst, test
   tests/test_i18n.py::test_data_tekstovi_pokriveni pada — mapa se
   MORA proširiti kad backend doda novi tekst. */

export const DATA_TX = {
  // ---- M40: profil poslovanja — generički sektorski opisi (GENERIC_ACTIVITY) ----
  'Kreditna institucija sa sjedištem u Republici Hrvatskoj (bankovni sektor).':
    'Credit institution headquartered in the Republic of Croatia (banking sector).',
  'Društvo za osiguranje sa sjedištem u Republici Hrvatskoj.':
    'Insurance company headquartered in the Republic of Croatia.',
  'Zatvoreni investicijski fond / investicijsko društvo uvršteno na Zagrebačkoj burzi.':
    'Closed-end investment fund / investment company listed on the Zagreb Stock Exchange.',
  'Društvo u djelatnosti turizma i ugostiteljstva (hoteli/marine/odmarališta).':
    'Company in the tourism and hospitality sector (hotels/marinas/resorts).',
  'Društvo u potrošačkom sektoru (proizvodnja/distribucija robe široke potrošnje).':
    'Company in the consumer sector (production/distribution of consumer goods).',
  'Industrijsko društvo (proizvodnja i/ili industrijske usluge).':
    'Industrial company (manufacturing and/or industrial services).',
  'Društvo koje upravlja grupom povezanih društava (holding/uprava grupe).':
    'Company managing a group of related companies (holding/group management).',
  'Telekomunikacijsko društvo.': 'Telecommunications company.',
  'Društvo u sektoru informacijskih tehnologija.':
    'Company in the information technology sector.',
  'Društvo u energetskom sektoru (energetska infrastruktura/usluge).':
    'Company in the energy sector (energy infrastructure/services).',
  'Brodarsko / pomorsko-prijevozničko društvo.':
    'Shipping / maritime transport company.',
  'Prijevozničko društvo.': 'Transport company.',
  'Društvo u graditeljstvu i inženjeringu.':
    'Construction and engineering company.',
  'Društvo za poslovanje nekretninama.': 'Real-estate company.',
  'Društvo u marikulturi/akvakulturi.': 'Company in mariculture/aquaculture.',
  'Uvršteno dioničko društvo (djelatnost prema sudskom/NACE registru).':
    'Listed joint-stock company (activity per the court/NACE register).',
  // ---- profil poslovanja — napomene i izvor ----
  'GENERIČKI OPIS — profil iz godišnjeg izvješća još nije ekstrahiran; opis navodi samo sektorsku činjenicu iz registra i ne tvrdi ništa specifično o firmi':
    'GENERIC DESCRIPTION — the profile from the annual report has not yet been extracted; the description states only the sector fact from the register and asserts nothing specific about the company',
  "samo činjenice iz izvješća s citatima; kvalitativne tvrdnje ('vodeći' i sl.) su TVRDNJE IZDAVATELJA, označene i citirane — platforma ih ne generira niti potvrđuje":
    "only facts from the report with citations; qualitative claims ('leading' etc.) are ISSUER CLAIMS, marked and quoted — the platform neither generates nor confirms them",
  'generički opis iz sektorskog registra (NACE)':
    'generic description from the sector register (NACE)',
  'Godišnje izvješće FY2025 (konsolidirano, PDF s EHO-a); ručna ekstrakcija s citatima po stranicama — API ekstrakcija nedostupna (kredit)':
    'Annual report FY2025 (consolidated, PDF from EHO); manual extraction with per-page citations — API extraction unavailable (credit)',

  // ---- indicators: naslovi grupa ----
  'Bilanca': 'Balance sheet',
  'Dividende': 'Dividends',
  'Izvedba dionice': 'Share performance',
  'Likvidnost i solventnost': 'Liquidity and solvency',
  'Novčani tok': 'Cash flow',
  'Po zaposlenom': 'Per employee',
  'Profitabilnost': 'Profitability',
  'Rast': 'Growth',
  'Učinkovitost': 'Efficiency',
  'Valuacija': 'Valuation',

  // ---- indicators: nazivi pokazatelja ----
  '52-tj maks': '52-wk high',
  '52-tj min': '52-wk low',
  'Broj zaposlenih': 'Employees',
  'DPS (zadnja)': 'DPS (latest)',
  'Dividenda': 'Dividend',
  'Dividendni prinos': 'Dividend yield',
  'Dobit/zaposlenom': 'Profit/employee',
  'Dug/kapital': 'Debt/equity',
  'Dugoročni dug': 'Long-term debt',
  'EBIT marža': 'EBIT margin',
  'EBITDA marža': 'EBITDA margin',
  'EPS YoY (kvartal)': 'EPS YoY (quarter)',
  'EV/Prihod': 'EV/Revenue',
  'Financijski CF': 'Financing CF',
  'Investicijski CF': 'Investing CF',
  'Kapital (ukupni)': 'Equity (total)',
  'Kratkoročni dug': 'Short-term debt',
  'Neto dug/EBITDA': 'Net debt/EBITDA',
  'Neto marža': 'Net margin',
  'Novac': 'Cash',
  'Novčani jaz': 'Cash conversion cycle',
  'Obrtaj imovine': 'Asset turnover',
  'Operativni CF': 'Operating CF',
  'Pokriće kamata': 'Interest coverage',
  'Povrat 1G': 'Return 1Y',
  'Povrat 1M': 'Return 1M',
  'Povrat 3G': 'Return 3Y',
  'Povrat 3M': 'Return 3M',
  'Povrat 6M': 'Return 6M',
  'Povrat YTD': 'Return YTD',
  'Prihod (TTM/FY)': 'Revenue (TTM/FY)',
  'Prihod YoY (kvartal)': 'Revenue YoY (quarter)',
  'Prihod/zaposlenom': 'Revenue/employee',
  'Sljedeći ex-datum': 'Next ex-date',
  'Tekući omjer': 'Current ratio',
  'Tržišna kap.': 'Market cap',
  'Ukupna imovina': 'Total assets',
  'Ukupne obveze': 'Total liabilities',
  'Zadnja isplata': 'Last payment',

  // ---- indicators: formule ----
  '(dug − novac) / EBITDA': '(debt − cash) / EBITDA',
  'DPS / cijena': 'DPS / price',
  'DPS × dionice / neto dobit': 'DPS × shares / net profit',
  'EBIT + amortizacija': 'EBIT + depreciation and amortisation',
  'EBIT / prihod': 'EBIT / revenue',
  'EBIT / rashodi od kamata': 'EBIT / interest expense',
  'EBITDA / prihod': 'EBITDA / revenue',
  'EV / Prihod': 'EV / revenue',
  'EV = trž. kap. + dug − novac − kratkoročna fin. imovina + manjinski udjeli':
    'EV = market cap + debt − cash − short-term financial assets + minority interests',
  'NT B)': 'cash-flow statement, section B',
  'NT C)': 'cash-flow statement, section C',
  'NT izvještaj': 'cash-flow statement',
  'Neto / prihod': 'net profit / revenue',
  'TFI Opći podaci': "TFI 'General information' sheet",
  "Z' (privatna varijanta): 0,717·WC/TA + 0,847·RE/TA + 3,107·EBIT/TA + 0,420·BVE/TL + 0,998·S/TA":
    "Z' (private-firm variant): 0.717·WC/TA + 0.847·RE/TA + 3.107·EBIT/TA + 0.420·BVE/TL + 0.998·S/TA",
  'bilanca': 'balance sheet',
  'close_zadnji / close_najbliži_ciljnom_danu − 1':
    'latest close / close nearest to target date − 1',
  'diskretni kvartal vs isti lanjski (Q2=H1−Q1...)':
    'discrete quarter vs same quarter last year (Q2=H1−Q1…)',
  'dividends tablica': 'dividends table',
  'dobavljači / materijalni troškovi × 365': 'payables / material costs × 365',
  'imovina − kapital (izvedeno)': 'assets − equity (derived)',
  'izdaci za dugotrajnu imovinu': 'payments for non-current assets',
  'kamatonosni': 'interest-bearing',
  'kamatonosni dug / knjiga': 'interest-bearing debt / book equity',
  'knjiga (matici) / dionice ex-trezor': 'book equity (parent) / shares ex-treasury',
  'knjiga matici / dionice ex-trezor': 'book equity (parent) / shares ex-treasury',
  'kratkotrajna imovina / kratkoročne obveze': 'current assets / current liabilities',
  'kumulativna derivacija': 'derived from cumulative periods',
  'kupci / prihod × 365': 'receivables / revenue × 365',
  'neto dobit / trž.kap': 'net profit / market cap',
  'neto dobit / ukupna imovina': 'net profit / total assets',
  'neto dobit matici / broj zaposlenih': 'net profit to parent / employees',
  'neto dobit matici / dionice ex-trezor': 'net profit to parent / shares ex-treasury',
  'neto dobit matici / knjiga matici': 'net profit to parent / book equity (parent)',
  'neto dobit matici po kvartalu / dionice — isti-na-isti':
    'quarterly net profit to parent / shares — like-for-like',
  'novac i ekvivalenti': 'cash and equivalents',
  'prihod / broj zaposlenih': 'revenue / employees',
  'prihod / imovina': 'revenue / assets',
  'trž.kap / knjiga (matici)': 'market cap / book equity (parent)',
  'trž.kap / neto dobit matici': 'market cap / net profit to parent',
  'trž.kap / operativni CF': 'market cap / operating CF',
  'trž.kap / prihod': 'market cap / revenue',
  'trž.kap / slobodni novčani tok': 'market cap / free cash flow',
  'zalihe / materijalni troškovi × 365 (COGS proxy)':
    'inventory / material costs × 365 (COGS proxy)',
  'Σ close klase × dionice klase': 'Σ class close × class shares',

  // ---- indicators: "zašto ovako" obrazloženja ----
  "Gruba mjera kad je dobit mala ili volatilna — prihod se teže 'friziran' od dobiti, ali ništa ne govori o marži.":
    "A rough measure when profit is small or volatile — revenue is harder to 'dress up' than profit, but it says nothing about margins.",
  'Kao EV/EBITDA, ali NAKON amortizacije — strože prema kapitalno intenzivnim firmama kojima se oprema stvarno troši.':
    'Like EV/EBITDA, but AFTER depreciation — stricter towards capital-intensive companies whose equipment genuinely wears out.',
  'Knjigovodstvena vrijednost po dionici — računovodstvena imovina minus obveze. To NIJE gotovina: većinom je dugotrajna imovina po (amortiziranom) trošku, pa je usporedba s cijenom smislena tek uz pitanje koliko ta imovina zarađuje (ROE).':
    'Book value per share — accounting assets minus liabilities. This is NOT cash: it is mostly non-current assets at (amortised) cost, so comparing it with the price only makes sense alongside the question of how much those assets earn (ROE).',
  'Koliko godina TRENUTNE zarade plaćate po današnjoj cijeni. Nazivnik je dobit koja pripada matici (bez manjinskih) — ista dobit iz koje se isplaćuje dividenda dioničarima.':
    "How many years of CURRENT earnings you pay at today's price. The denominator is profit attributable to the parent (excluding minorities) — the same profit dividends are paid from.",
  'Koliko se plaća po euru prihoda cijelog poslovanja — neovisno o tome financira li se firma dugom ili kapitalom.':
    'What you pay per euro of revenue of the whole business — regardless of whether the company is financed with debt or equity.',
  "Koliko se plaća po euru vlastitog kapitala. Sam po sebi ne kaže je li dionica 'jeftina': kapital koji zarađuje više od zahtijevanog prinosa OPRAVDANO vrijedi iznad knjige, a kapital s niskim povratom ispod nje — ključ je ROE naspram troška kapitala.":
    "What you pay per euro of book equity. By itself it does not say whether the stock is 'cheap': equity earning more than the required return JUSTIFIABLY trades above book, and low-return equity below it — the key is ROE versus the cost of equity.",
  'Novac iz poslovanja umjesto računovodstvene dobiti — otporniji na nenovčane stavke (rezervacije, revalorizacije).':
    'Cash from operations instead of accounting profit — more resistant to non-cash items (provisions, revaluations).',
  'Novac koji NAKON ulaganja stvarno ostaje vlasnicima — najbliže onome što DCF diskontira.':
    'Cash that ACTUALLY remains for owners after investment — closest to what a DCF discounts.',
  "Obrnuti P/E — 'prinos zarade' usporediv s prinosom obveznice: koliko firma zaradi na svakih 100 € tržišne vrijednosti.":
    "Inverted P/E — an 'earnings yield' comparable to a bond yield: how much the company earns per €100 of market value.",
  'Omjer neovisan o strukturi financiranja i amortizacijskim politikama. Brojnik i nazivnik pokrivaju ISTI opseg: konsolidirana EBITDA uključuje 100% kćeri, pa EV uključuje i manjinske udjele; EBITDA je TTM (zadnjih 12 mj.) gdje kvartali postoje — zato se brojka može razlikovati od izračuna s godišnjom EBITDA-om ili bez manjinskih udjela.':
    'A ratio independent of financing structure and depreciation policies. Numerator and denominator cover the SAME scope: consolidated EBITDA includes 100% of subsidiaries, so EV also includes minority interests; EBITDA is TTM (last 12 months) where quarters exist — which is why the figure can differ from calculations using annual EBITDA or excluding minorities.',
  "Vrijednost CIJELOG poslovanja, ne samo dioničara: dug se dodaje (i vjerovnici imaju pravo na taj novac), novac i kratkoročna financijska imovina se odbijaju (kupac ih 'dobije natrag'), a manjinski udjeli se DODAJU jer konsolidirani rezultati uključuju 100% kćeri — pa i dio koji pripada drugima mora biti u istoj mjeri. Zato se naš EV zna razlikovati od portala koji manjinske udjele preskaču.":
    "The value of the WHOLE business, not just shareholders: debt is added (creditors also have a claim on that cash), cash and short-term financial assets are deducted (a buyer 'gets them back'), and minority interests are ADDED because consolidated results include 100% of subsidiaries — so the part belonging to others must be in the same measure. This is why our EV can differ from portals that skip minority interests.",
  'Zarada po dionici: dobit koja pripada matici podijeljena brojem dionica bez trezorskih. TTM (zadnjih 12 mj.) gdje kvartali postoje — svježije od zadnjeg godišnjeg izvješća.':
    'Earnings per share: profit attributable to the parent divided by shares excluding treasury shares. TTM (last 12 months) where quarters exist — fresher than the latest annual report.',
  'Zbrajamo SVE klase dionica (svaku po svojoj cijeni), a trezorske isključujemo — firma ne može biti vlasnik same sebe, pa te dionice ne nose ekonomsku vrijednost.':
    'We sum ALL share classes (each at its own price) and exclude treasury shares — a company cannot own itself, so those shares carry no economic value.',

  // ---- indicators: n/p razlozi ----
  'banka: prihod = operativni prihod (vidi P/TOI)': 'bank: revenue = operating income (see P/TOI)',
  'broj zaposlenih još nije u bazi za ovu firmu': 'employee count is not yet in our database for this company',
  'financijska firma': 'financial company',
  'financijska firma — dug je posao, ne struktura': 'financial company — debt is the business, not the capital structure',
  'kvartali još nisu u bazi za usporedbu': 'quarters are not yet in the database for comparison',
  'kvartali nedostupni': 'quarterly data unavailable',
  'n/p za banke/osiguranje': 'n/a for banks/insurers',
  'n/p za banke/osiguranje — struktura bilance je posao': 'n/a for banks/insurers — the balance-sheet structure is the business',
  'n/p za financijske firme': 'n/a for financial companies',
  'n/p za holding (nema robni ciklus)': 'n/a for holding companies (no goods cycle)',
  'nedostaju DSO/DIO/DPO': 'DSO/DIO/DPO missing',
  'nedostaju ulazi (WC/RE/EBIT/knjiga)': 'inputs missing (WC/RE/EBIT/book value)',
  'nema cijene': 'no price',
  'nema dobiti/dionica': 'no profit or share count',
  'nema evidentirane isplaćene dividende (moguć samo prijedlog — vidi nadolazeći ex-datum)':
    'no recorded paid dividend (only a proposal may exist — see the upcoming ex-date)',
  'nema najave': 'no announcement',
  'nema podataka': 'no data',
  'nema u bazi': 'not in the database',
  'nema ulaza': 'inputs missing',
  'nema zapisa u bazi': 'no records in the database',
  'serija cijena prekratka': 'price series too short',
  'stavke još nisu u bazi': 'items are not yet in the database',
  'trošak kamata nije u bazi': 'interest expense is not in the database',

  // ---- indicators: osnovice (fiksne) i napomena ----
  'trž.kap + dug − novac − kratk. fin. imovina + manjinski (zadnja bilanca)':
    'market cap + debt − cash − short-term fin. assets + minorities (latest balance sheet)',
  'zadnja isplata / zadnja cijena': 'last payment / last price',
  'zadnji EOD × dionice ex-trezor': 'latest EOD × shares ex-treasury',
  'n/p': 'n/a',
  'TTM = zadnji FY + tekući YTD − lanjski isti YTD (samo tokovne stavke); bilanca = zadnje objavljeno stanje; FY se nikad ne prikazuje kao TTM. Formule su opisane u Metodologiji.':
    'TTM = last FY + current YTD − same YTD last year (flow items only); balance sheet = latest reported position; FY is never presented as TTM. The formulas are described in the Methodology.',

  // ---- global peers ----
  'globalni peerovi su KONTEKST — ne ulaze u sidro fer-zone (v2 §8); cross-market razlike (rast, likvidnost, veličina, trošak kapitala tržišta) objašnjavaju dio raskoraka u multiplima':
    'global peers are CONTEXT — they do not enter the fair-value anchor (v2 §8); cross-market differences (growth, liquidity, size, market cost of capital) explain part of the gap in multiples',
  'multipli globalnih peera zahtijevaju ručni snapshot s izvorom i datumom — vanjski tržišni podaci nisu dostupni automatskim putem; do unosa snapshotta prikazuje se samo kurirana lista':
    'global peer multiples require a manual snapshot with source and date — external market data is not available automatically; until a snapshot is entered only the curated list is shown',
  'EU': 'EU',
  'globalno': 'global',
  'HR/regija': 'HR/region',

  // ---- news (tab Novosti) ----
  'službene objave izdavatelja s EHO-a (zse.hr) — bez medijskih napisa i bez komentara platforme; prazno = nema objava u bazi':
    'official issuer announcements from EHO (zse.hr) — no media articles and no platform commentary; empty = no announcements in the database',

  // ---- StockPage: financials_3y / trend labeli ----
  'Prihodi': 'Revenue',
  'Ukupni operativni prihod': 'Total operating income',
  'Neto dobit matici': 'Net profit to parent',
  'Neto kamatni prihod': 'Net interest income',
  'Neto prihod od naknada': 'Net fee and commission income',
  'Operativni novčani tok': 'Operating cash flow',
  'Operativni troškovi': 'Operating expenses',
  'Rezervacije (trošak rizika)': 'Provisions (cost of risk)',
  'Trošak rizika': 'Cost of risk',
  'EPS (dobit matici / dionica)': 'EPS (profit to parent / shares)',
  'konsolidirano, godišnje (v_financials_current); EPS uz kanonski današnji broj dionica bez trezorskih; prazno = nema u bazi, ne procjenjuje se':
    'consolidated, annual (v_financials_current); EPS uses the canonical current share count excluding treasury shares; blank = not in the database, no estimate is made',

  // ---- StockPage: bilanca / poluga / segmenti ----
  'net_debt = debt_short + debt_long − novac (izračun iz ekstrakcije)':
    'net_debt = debt_short + debt_long − cash (computed from extraction)',
  '−net_debt (dug − novac, izvedeno iz ekstrakcije)':
    '−net_debt (debt − cash, derived from extraction)',
  'tekući omjer: kratkoročne stavke nisu u bazi':
    'current ratio: short-term items are not in the database',
  'n/p — kod osiguratelja/banaka depoziti, pričuve i obveze iz ugovora nisu financijski dug pa net_debt i net_debt/EBITDA nemaju smisla (sektorski KPI dolaze zasebno)':
    'n/a — for insurers/banks, deposits, reserves and liabilities under contracts are not financial debt, so net_debt and net_debt/EBITDA are not meaningful (sector KPIs are provided separately)',
  'holding konsolidira osiguratelja — grupni net_debt/EBITDA uzeti s oprezom (miješa financijski i operativni dio)':
    'the holding consolidates an insurer — treat group net_debt/EBITDA with caution (it mixes the financial and operating parts)',
  "n/p — Σ segmenata uključuje premije osiguranja, a grupni 'revenue' u bazi ne; usporedivi ukupni prihod (bilj. o segmentima) nije među kanonskim stavkama":
    "n/a — the Σ of segments includes insurance premiums while the group 'revenue' in the database does not; a comparable total income (segment note) is not among the canonical items",
  'ostatak = eliminacije/centar; segmentne brojke uključuju unutargrupne odnose (bilj. o segmentima); Σ EBITDA nepotpun — bez EBITDA: Osiguranje':
    'remainder = eliminations/centre; segment figures include intra-group relations (segment note); Σ EBITDA incomplete — without EBITDA: Insurance',

  // ---- StockPage: bank KPI ----
  "bankovni KPI: 'izvučeno' = objavljena brojka s izvorom u fundamentima; 'izračun' = formula nad izvučenim stavkama; bez podatka -> 'nema u bazi', ne nula. OGRADA za YoY: FY-1 može dolaziti iz GFI obrasca a FY0 iz revidiranog godišnjeg izvješća — definicije bilančnih linija mogu odstupati":
    "bank KPIs: 'extracted' = a published figure with its source in the fundamentals; 'computed' = a formula over extracted items; where data is missing -> 'not in the database', not zero. CAVEAT for YoY: FY-1 may come from the GFI form while FY0 comes from the audited annual report — definitions of balance-sheet lines may differ",
  'izračun iz FY0 vs FY-1': 'computed from FY0 vs FY-1',
  'izračun: NII / imovina na kraj godine (nema FY-1)': 'computed: NII / year-end assets (no FY-1)',
  'izračun: NII / prosječna imovina (FY0, FY-1)': 'computed: NII / average assets (FY0, FY-1)',
  'izračun: krediti klijentima / depoziti klijenata': 'computed: customer loans / customer deposits',
  'izračun: neto dobit matici / kapital matici (kraj godine)':
    'computed: net profit to parent / parent equity (year-end)',
  'izračun: neto dobit matici / ukupna imovina': 'computed: net profit to parent / total assets',
  'izračun: |operativni troškovi| / ukupni operativni prihod':
    'computed: |operating expenses| / total operating income',
  'izračun: −rezervacije / krediti (kraj godine); negativno = neto otpuštanje':
    'computed: −provisions / loans (year-end); negative = a net release',
  'izvučeno (bilj. o regulatornom kapitalu)': 'extracted (regulatory-capital note)',
  'izvučeno (regulatory)': 'extracted (regulatory)',

  // ---- StockPage: vlasništvo / top10 ----
  'promjene = usporedba zadnja dva snapshota; udjeli u p.p.':
    'changes = comparison of the last two snapshots; stakes in p.p.',
  'samo jedan snapshot u bazi — prikazuje se stanje s datumom, bez promjena (povijest se gradi mjesečnim snapshotima)':
    'only one snapshot in the database — the dated position is shown without changes (history is built from monthly snapshots)',
  'skrbnički/zbirni računi (oznaka) nisu stvarni krajnji vlasnici — dionice drže za klijente':
    'custody/omnibus accounts (flagged) are not the actual ultimate owners — they hold the shares on behalf of clients',
  'u bazi nema zabilježenih većinskih imatelja za ovu firmu — free float nepoznat (ne procjenjuje se)':
    'no majority holders are recorded in the database for this company — free float unknown (no estimate is made)',

  // ---- StockPage: valuacija — labeli metoda ----
  'Dividendni diskont': 'Dividend discount',
  'Opravdani P/B (ROE)': 'Justified P/B (ROE)',
  'Peer usporedba (comps)': 'Peer comparison (comps)',
  'Rezidualni dohodak (RI)': 'Residual income (RI)',

  // ---- StockPage: valuacija — skip razlozi ----
  'default multiple / nekalibrirani peer P/E — nisu tržišno kalibrirane':
    'default multiples / uncalibrated peer P/E — not market-calibrated',
  'financije — FCF loše definiran': 'financials — FCF poorly defined',
  'ne isplaćuje (ili nepoznata) dividenda': 'no dividend paid (or unknown)',
  'nema materijalnih udjela ni odvojivih segmenata (npr. CROS: jedan biznis)':
    'no material stakes or separable segments (e.g. CROS: a single business)',
  'nema operativni CF i capex (ni brojčani guidance za proxy)':
    'operating CF and capex unavailable (and no numeric guidance for a proxy)',
  'operativni CF i capex postoje, ali ispod praga pouzdanosti (nerevidiran/kvartalni) ili obrtnim kapitalom iskrivljen jednogodišnji FCF — DCF se ne sidri na nesigurnom ulazu (comps nosi vrednovanje)':
    'operating CF and capex exist but below the confidence threshold (unaudited/quarterly) or the single-year FCF is distorted by working capital — the DCF is not anchored on an uncertain input (comps carries the valuation)',
  'nema usporedivog osiguratelja na ZSE (kriteriji odabira peera opisani u Metodologiji)':
    'no comparable insurer on the ZSE (peer selection criteria are described in the Methodology)',
  'TTM se ne gradi: nema novijih interima od godišnjeg — vrednuje se iz zadnjeg godišnjeg izvješća':
    'TTM is not built: no interims newer than the annual report — valued from the latest annual report',

  // ---- StockPage: valuacija — rast, pretpostavke, sanity ----
  'godišnje izvješće': 'annual report',
  'godišnji podatak': 'annual data point',
  'izvor': 'source',
  'pretpostavka': 'assumption',
  'prolazi': 'passes',
  'prolazi (uz dividendni pod)': 'passes (with the dividend floor)',
  'održivi rast': 'sustainable growth',
  'održivi rast (kratka serija — bez g_obs)': 'sustainable growth (short series — no g_obs)',
  'negativan g1 — višegodišnje skupljanje dokazano ≥3g serijom':
    'negative g1 — a multi-year contraction evidenced by a ≥3y series',
  'vrijednosti su ručno unesene s datumom (tržišni izvori nedostupni iz build okruženja) i označene exact_unverified; rizik zemlje se računa točno jednom — u CRP-u, ne u rf-u ni u ERP-u (postupak u Metodologiji)':
    'values were entered manually with a date (market sources are unavailable from the build environment) and flagged exact_unverified; country risk is counted exactly once — in the CRP, not in rf nor in the ERP (procedure in the Methodology)',
  'zarada/prihodi/ROE računaju se na zadnjih 12 mjeseci (zadnje godišnje + ovogodišnji kvartali − lanjski kvartali) — v3 FAZA G; kvartalni izvještaji su nerevidirani':
    "earnings/revenue/ROE are computed over the trailing 12 months (latest annual + this year's quarters − last year's quarters) — v3 PHASE G; quarterly reports are unaudited",

  // ---- StockPage: value vs book / SOTP / rizici ----
  'Zašto je naša procjena ispod knjigovodstvene vrijednosti': 'Why our estimate is below book value',
  'Zašto je naša procjena iznad knjigovodstvene vrijednosti': 'Why our estimate is above book value',
  'KONČAR D&ST (KODT)': 'KONCAR D&ST (KODT)',
  'KONČAR standalone (ex-uvrštene kćeri)': 'KONCAR standalone (excl. listed subsidiaries)',
  'neto novac (−neto dug) centra/grupe': 'net cash (−net debt) of the centre/group',
  'tekuća cijena vs OVAJ (konzervativni) NAV; povijesna serija cijena↔NAV je kalibrirana — vidi izvor holding diskonta u pretpostavkama':
    'current price vs THIS (conservative) NAV; the historical price↔NAV series is calibrated — see the source of the holding discount in the assumptions',
  'OVISNOST O KĆERIMA': 'DEPENDENCE ON SUBSIDIARIES',

  // ---- StockPage: data/MAR napomene ----
  'Informativni prikaz metoda, raspona i pretpostavki iz javno objavljenih izvješća; nije investicijski savjet ni preporuka.':
    'An informative overview of methods, ranges and assumptions from publicly released reports; not investment advice or a recommendation.',
  'činjenični kontekst izveden iz podataka ovog exporta — bez ocjena i preporuka; zaključak je čitateljev':
    "factual context derived from the data in this export — no ratings or recommendations; the conclusion is the reader's",

}

/* Pattern pravila za stringove s dinamičkim dijelovima (datumi, n=,
   popisi peera). Primjenjuju se redom NAKON promašaja exact mape. */
const PATTERNS = [
  // M40: izvor profila — ručna ekstrakcija (put do datoteke ostaje kako jest)
  [/ručna ekstrakcija u Claude Code sesiji \(([^,]+), početak izvješća; ista shema kao API pipeline\)/g,
    'manual extraction in a Claude Code session ($1, start of the report; same schema as the API pipeline)'],
  [/Kvartalno/g, 'Quarterly'],
  [/ilikvidna \(indikativno\)/g, 'illiquid (indicative)'],
  [/negativan izvedeni kvartal \(restatement\?\) -> isključen/g,
    'negative derived quarter (restatement?) -> excluded'],
  // izvor peer skupa nosi 'TICKER: ' prefiks -> pattern umjesto exact mape
  [/peer skup nije kalibriran — na ZSE nema dovoljno usporedivih firmi u sektoru \(kriteriji odabira peera opisani u Metodologiji; regionalni peeri se ne koriste\) -> peer multipli OSTAJU placeholder \(P\/E 12, P\/B 1,5\), a multipl-metode nose NISKU pouzdanost \(0,3\)/g,
    'the peer set is not calibrated — the ZSE does not have enough comparable companies in this sector (peer selection criteria are described in the Methodology; regional peers are not used) -> peer multiples REMAIN placeholders (P/E 12, P/B 1.5) and multiple-based methods carry LOW reliability (0.3)'],
  [/peer multipli = MEDIJAN iz baze \(zadnje cijene \+ zadnje godišnje kons\. financije\):/g,
    'peer multiples = MEDIAN from our database (latest prices + latest annual cons. financials):'],
  [/Skup \[/g, 'Set ['],
  [/\(kriteriji odabira u Metodologiji; sektorski skup unutar praćenog univerzuma, bez cirkularnosti\)/g,
    '(selection criteria in the Methodology; sector set within the covered universe, no circularity)'],
  [/USKI SKUP \(n=(\d+)\) -> snižena pouzdanost multipl-metoda\./g,
    'NARROW SET (n=$1) -> reduced reliability of multiple-based methods.'],
  [/Po peeru:/g, 'Per peer:'],
  [/Ručni snapshot multipla:/g, 'Manual multiples snapshot:'],

  // ---- trend naracije (Prihodi/EBITDA marža, smjerovi) ----
  [/: samo (\d{4})\. u bazi \(([\d.,]+) M€\) — trend se ne računa iz jedne godine\./g,
    ': only $1 in the database ($2 M€) — a trend is not computed from a single year.'],
  [/^Prihodi: /, 'Revenue: '],
  [/^Ukupni operativni prihod: /, 'Total operating income: '],
  [/Smjer: rast/g, 'Direction: rising'],
  [/Smjer: pad/g, 'Direction: falling'],
  [/Smjer: stabilno/g, 'Direction: stable'],
  [/; ukupno kroz razdoblje /g, '; total over the period '],
  [/ marža: /g, ' margin: '],
  [/— jedna godina u bazi\./g, '— a single year in the database.'],
  [/Nedostaje: /g, 'Missing: '],
  [/n\/p za financijski sektor — vidi bankovne pokazatelje/g,
    'n/a for the financial sector — see the bank indicators'],
  [/n\/p za financijski sektor \(osiguranje: premije\/pričuve, ne operativna marža\)/g,
    'n/a for the financial sector (insurance: premiums/reserves, not an operating margin)'],
  [/naracija je izvedena isključivo iz brojki u bazi \(bez ocjena\); smjer = usporedba ruba razdoblja uz prag ±/g,
    'the narration is derived solely from figures in the database (no judgements); direction = comparison of the period edges with a threshold of ±'],

  // ---- value vs book (fer-zona naspram knjige) ----
  [/Fer-zona \(([^)]+)\) niža je od knjigovodstvene vrijednosti \(([^)]+) po dionici\)\./g,
    'The fair-value zone ($1) is below the book value ($2 per share).'],
  [/Fer-zona \(([^)]+)\) viša je od knjigovodstvene vrijednosti \(([^)]+) po dionici\)\./g,
    'The fair-value zone ($1) is above the book value ($2 per share).'],
  [/To je posljedica prinosnog pristupa, ne previda: firma na vlastitom kapitalu trenutačno zarađuje oko ([-\d.,]+ %) godišnje, a ulagač za ovaj rizik traži ([\d.,]+ %) — kapital koji trajno zarađuje manje od zahtijevanog prinosa u pravilu vrijedi manje od svoje knjige\./g,
    'That is a consequence of the earnings-based approach, not an oversight: the company currently earns about $1 a year on its equity, while investors require $2 for this risk — equity that permanently earns less than the required return is, as a rule, worth less than its book value.'],
  [/Knjigovodstvena vrijednost pritom nije gotovina: većinom je to dugotrajna imovina po amortiziranom trošku, a punu knjigu bi opravdala tek prodaja imovine blizu tih vrijednosti — što procjena poslovanja koje nastavlja poslovati ne pretpostavlja\./g,
    'Book value is not cash: it is mostly non-current assets at amortised cost, and only an asset sale near those values would justify the full book value — which a going-concern valuation does not assume.'],
  [/Tržišna cijena \(([^)]+)\) stoji između te dvije kotve — koliko vrijedi mogućnost prodaje imovine ili oporavka profitabilnosti, zaključak je čitateljev\./g,
    "The market price ($1) sits between those two anchors — how much the option of selling assets or a recovery in profitability is worth is the reader's conclusion."],
  [/Firma na vlastitom kapitalu zarađuje oko ([-\d.,]+ %) godišnje, više od zahtijevanog prinosa od ([\d.,]+ %) — kapital koji trajno zarađuje iznad tražene stope opravdano vrijedi više od knjige \(ista logika po kojoj slab povrat vuče vrijednost ispod nje\)\. Zaključak je čitateljev\./g,
    "On its equity the company earns about $1 a year, more than the required return of $2 — equity that permanently earns above the required rate justifiably trades above book value (the same logic by which a weak return drags value below it). The conclusion is the reader's."],

  // ---- zone_note (triangulacija, sidra, dividendni pod) ----
  [/dvije kvalificirane metode razmaknute ([\d.,]+)% > ([\d.,]+)% — NE prosječi \(v([\d.]+) §([\d.]+)\): sredinu nosi sidro '([a-z_]+)', druga metoda je kontekst/g,
    "two qualified methods sit $1% apart > $2% — NOT averaged (v$3 §$4): the midpoint is carried by the '$5' anchor, the other method is context"],
  [/zona = MEDIJAN kvalificiranih metoda \(/g, 'zone = MEDIAN of the qualified methods ('],
  [/± osjetljivost primarnog sidra /g, '± sensitivity of the primary anchor '],
  [/— v([\d.]+) triangulacija/g, '— v$1 triangulation'],
  [/isključeno \(nepozitivna baza\/conf\): /g, 'excluded (non-positive base/conf): '],
  [/isključeno sidro s degeneriranom osjetljivošću \(raspon > ([\d.,]+)% baze\): /g,
    'anchor excluded due to degenerate sensitivity (range > $1% of the base): '],
  [/sidra isključena zbog degenerirane osjetljivosti: /g,
    'anchors excluded due to degenerate sensitivity: '],
  [/minimalna širina zone ±([\d.,]+)% \(osjetljivost degenerirana\)/g,
    'minimum zone width of ±$1% (degenerate sensitivity)'],
  [/DIVIDENDNI POD \(v([\d.]+)\): V_div ([\d.,]+) € uključen u medijan kvalificiranih metoda, donji rub podignut na pod \(([\d.,]+) → ([\d.,]+)\) — održiva dividenda podržava vrijednost, ne gasi zonu/g,
    'DIVIDEND FLOOR (v$1): V_div $2 € included in the median of the qualified methods, lower edge raised to the floor ($3 → $4) — a sustainable dividend supports the value, it does not void the zone'],
  [/sidrena metoda nije dostupna — zona je min–max pozitivnih baza \(fallback\); vidi 'skipped' za razlog/g,
    "the anchor method is unavailable — the zone is the min–max of positive bases (fallback); see 'skipped' for the reason"],
  [/Sve metode zajedno raspinju ([-\d.,]+)–([\d.,]+) € \(raspon ([\d.,]+)%\) — svaka leća mjeri drugo svojstvo; sidrena zona je uža\./g,
    'All methods together span $1–$2 € (a $3% range) — each lens measures a different property; the anchored zone is narrower.'],

  // ---- market implied (implicirani g / r) ----
  [/uz naš r=([\d.,]+)% cijena implicira trajni rast ([A-Za-z]+)-a ~([+\-][\d.,]+)% godišnje/g,
    'at our r=$1% the price implies perpetual $2 growth of ~$3% per year'],
  [/uz naš trajni rast ([\d.,]+)% i ([A-Z]+) ([-\d.,]+)% cijena implicira trošak kapitala ~([-\d.,]+)% \(naš: ([\d.,]+)%\)/g,
    'at our perpetual growth of $1% and $2 of $3% the price implies a cost of capital of ~$4% (ours: $5%)'],
  [/uz naš trajni rast ([\d.,]+)% cijena implicira trošak kapitala ~([-\d.,]+)% \(naš: ([\d.,]+)%\)/g,
    'at our perpetual growth of $1% the price implies a cost of capital of ~$2% (ours: $3%)'],
  [/Tržišna cijena implicira ~([+\-][\d.,]+)% trajnog rasta godišnje/g,
    'The market price implies ~$1% perpetual annual growth'],
  [/ \/ multipl P\/E /g, ' / a P/E multiple of '],
  [/Tržišna cijena implicira multipl P\/E /g, 'The market price implies a P/E multiple of '],
  [/Tržišna cijena implicira /g, 'The market price implies '],
  [/naš kompozitni rast \(serija\/održivi\/terminal\) je /g,
    'our composite growth (series/sustainable/terminal) is '],
  [/— razlika je upitna jer implicirani rast odstupa više od ([\d.,]+) p\.b\. od našeg kompozitnog rasta \(serija\/održivi\/terminal\)\./g,
    '— the difference is questionable because the implied growth deviates by more than $1 p.p. from our composite growth (series/sustainable/terminal).'],
  [/— razlika je plauzibilna jer implicirani rast je unutar ([\d.,]+) p\.b\. od našeg kompozitnog rasta\./g,
    '— the difference is plausible because the implied growth is within $1 p.p. of our composite growth.'],
  [/— razlika je neprovjerljiva bez kompozitne stope rasta jer kompozitna stopa rasta nije izračunata\./g,
    '— the difference is unverifiable without a composite growth rate because the composite growth rate has not been calculated.'],
  [/Ovo je usporedba implikacija, ne preporuka; zaključak je čitateljev\./g,
    "This is a comparison of implications, not a recommendation; the conclusion is the reader's."],

  // ---- likvidnost / free float / trgovanje ----
  [/Novi Siemens JV \((\d+)%\): nema podataka u bazi \(udjel (\d+)%\) — dio NIJE u NAV-u/g,
    'New Siemens JV ($1%): no data in the database ($2% stake) — this part is NOT in the NAV'],
  [/manjinski free float \(~([\d.,]+)%\) znači plitku knjigu naloga — vidi oznaku likvidnosti uz cijenu/g,
    'a minority free float (~$1%) means a shallow order book — see the liquidity flag next to the price'],
  [/free float približno ([\d.,]+)%/g, 'free float approximately $1%'],
  [/zadnja trgovina (\d{4}-\d{2}-\d{2}): (\d+) kom \/ ([\d.,]+) € prometa \((\d+) d\)/g,
    'last trade $1: $2 shares / $3 € turnover ($4 d)'],
  [/u dostupnim podacima \(od ([^)]+)\) nema zabilježene trgovine — zadnji close je indikativan, ne transakcijski/g,
    'no trades recorded in the available data (since $1) — the latest close is indicative, not transactional'],
  [/cijena bez prometa je indikativna; flag: low = dnevni promet < ([\d.,]+) € ili > (\d+) d bez trgovine; very_low = < (\d+) kom ili > (\d+) d/g,
    'a price without turnover is indicative; flag: low = daily turnover < $1 € or > $2 d without a trade; very_low = < $3 shares or > $4 d'],
  [/− Σ top (\d+) dioničara \(snapshot /g, '− Σ top $1 shareholders (snapshot '],
  [/ZSE stranica papira \(izvor SKDD\)/g, 'ZSE security page (source: SKDD)'],
  [/aproksimacija — imatelji izvan top (\d+) nisu obuhvaćeni/g,
    'an approximation — holders outside the top $1 are not covered'],

  // ---- valuacija: skip razlozi / ROE pravilo / TTM sanity ----
  [/RI predložak je za financijske firme \(banka\/osiguranje\), ne /g,
    'the RI template is for financial companies (bank/insurance), not '],
  [/arhetip '([a-z_]+)': opravdani P\/B je ovdje leća\/pokazatelj, ne metoda \(v([\d.]+) §([\d.]+)\/§([\d.]+)\)/g,
    "archetype '$1': justified P/B is a lens/indicator here, not a method (v$2 §$3/§$4)"],
  [/ROE pravilo/g, 'ROE rule'],
  [/nema (\d)g serije za medijan/g, 'no $1y series for the median'],
  [/(\d)g medijan/g, '$1y median'],
  [/TTM se ne gradi: TTM izvan sanity raspona \(([-\d.,]+)× godišnjeg\) — koristi se godišnje — vrednuje se iz zadnjeg godišnjeg izvješća/g,
    'TTM is not built: TTM outside the sanity range ($1× annual) — the annual figure is used — valued from the latest annual report'],
  [/TTM se ne gradi: nema prošlogodišnjeg q(\d) interima za usporedbu — TTM se ne gradi — vrednuje se iz zadnjeg godišnjeg izvješća/g,
    'TTM is not built: no prior-year q$1 interim for comparison — TTM is not built — valued from the latest annual report'],

  // ---- valuacija: rast (g_source, badges, origin) ----
  [/kapitalni trajni g ([\d.,]+)% \(sidro zone je ([a-z_]+) — ista pretpostavka rasta kojom je zona izračunata\)/g,
    'equity perpetual g of $1% (the zone anchor is $2 — the same growth assumption used to compute the zone)'],
  [/terminalni g ([\d.,]+)% \(sidro zone je ([a-z_]+)\)/g,
    'terminal g of $1% (the zone anchor is $2)'],
  [/u bazi nema tri godišnja izvješća pa kompozitni g(\d) nastaje bez signala serije — iz održivog rasta \(ROE × zadržana dobit\) i terminalnog sidra, uz cap (\d+)%; jedna godišnja usporedba nije stopa rasta \(v([\d.]+)\)/g,
    'the database lacks three annual reports, so the composite g$1 is formed without a series signal — from sustainable growth (ROE × retained earnings) and the terminal anchor, capped at $2%; a single annual comparison is not a growth rate (v$3)'],

  // ---- valuacija: pretpostavke (beta, premija nelikvidnosti, mar_note) ----
  [/Procjena počiva na označenim pretpostavkama: /g, 'The estimate rests on the flagged assumptions: '],
  [/β = ([\d.,]+) \(sektorska \(nema serije\)\)/g, 'β = $1 (sector beta (no series))'],
  [/β = ([\d.,]+) \(sektorska \(nelikvidno\)\)/g, 'β = $1 (sector beta (illiquid))'],
  [/vlastita burzovna serija ove dionice ne daje pouzdanu betu \(nelikvidnost\/kratka serija\) — korištena je sektorska beta \(Damodaran, Europa\)/g,
    "this stock's own exchange series does not yield a reliable beta (illiquidity/short series) — the sector beta was used (Damodaran, Europe)"],
  [/finalna vrijednost ograničena na raspon \[/g, 'final value clamped to the range ['],
  [/postupak je opisan u Metodologiji/g, 'the procedure is described in the Methodology'],
  // M43-5: nova formulacija premije nelikvidnosti (izvor u beta_discipline);
  // MORA biti prije generičkog '494' hvatača (inače bi prefiks bio pojeden)
  [/premija nelikvidnosti \+([\d.,]+) p\.b\. na traženi prinos: (\d+)\/(\d+) trgovanih dana \(([\d.,]+)%\), prosj\. promet ([\d.,]+) €\/dan — izlazak iz pozicije nosi stvaran trošak \(širok raspon cijena, plitka knjiga naloga\), a niska sektorska beta taj rizik ne obuhvaća; stupnjevano: /g,
    'illiquidity premium of +$1 p.p. on the required return: $2/$3 traded days ($4%), avg. daily turnover $5 €/day — exiting a position carries a real cost (wide price range, shallow order book), and the low sector beta does not capture that risk; tiered: '],
  [/<([\d.,]+)% dana ili <([\d.,]+) €\/dan -> \+([\d.,]+) p\.b\., ispod praga \(([\d.,]+)% dana \/ ([\d.,]+) €\/dan\) -> \+([\d.,]+) p\.b\. Nelikvidnosna premija je standardan dodatak na CAPM za slabo trgovane dionice\./g,
    '<$1% of days or <$2 €/day -> +$3 p.p., below the threshold ($4% of days / $5 €/day) -> +$6 p.p. An illiquidity premium is a standard add-on to CAPM for thinly traded stocks.'],
  // (stara formulacija 'na r:' zadržana radi eventualnih zaostalih exporta)
  [/premija nelikvidnosti \+([\d.,]+) p\.b\. na r: (\d+)\/(\d+) trgovanih dana \(([\d.,]+)%\), prosj\. promet ([\d.,]+) €\/dan — izlazak iz pozicije nosi stvaran trošak \(širok spread, plitka knjiga\); stupnjevano: /g,
    'illiquidity premium of +$1 p.p. on r: $2/$3 traded days ($4%), avg. daily turnover $5 € — exiting a position carries a real cost (wide spread, shallow order book); tiered: '],
  [/<([\d.,]+)% dana ili <([\d.,]+) €\/dan -> \+([\d.,]+) p\.b\., ispod praga \(([\d.,]+)% dana \/ ([\d.,]+) €\/dan\) -> \+([\d.,]+) p\.b\. Literatura: nelikvidnosna premija je standardan dodatak na CAPM za netrgovane\/slabo trgovane dionice\./g,
    '<$1% of days or <$2 €/day -> +$3 p.p., below the threshold ($4% of days / $5 €/day) -> +$6 p.p. Literature: an illiquidity premium is a standard add-on to CAPM for non-traded/thinly traded stocks.'],
  // M43-4/M43-5: raspis izvora troška kapitala (r-source explainer)
  [/nerizična stopa, tržišna premija i premija rizika zemlje referentne su tržišne veličine; rizik Hrvatske uračunava se točno jednom — kroz premiju rizika zemlje, ne kroz nerizičnu stopu ni tržišnu premiju/g,
    "the risk-free rate, market premium and country-risk premium are reference market quantities; Croatia's risk is counted exactly once — through the country-risk premium, not through the risk-free rate or the market premium"],
  [/Dodatno se dodaje premija nelikvidnosti ([\d.,]+) p\.b\. jer se ova dionica rijetko trguje — izlazak iz pozicije nosi stvaran trošak, a niska beta taj rizik ne obuhvaća; zato je traženi prinos viši \(i fer-vrijednost niža\) nego kod likvidnih dionica/g,
    'An illiquidity premium of $1 p.p. is added because this stock trades rarely — exiting a position carries a real cost and the low beta does not capture that risk; the required return is therefore higher (and the fair value lower) than for liquid stocks'],
  [/postupak u Metodologiji/g, 'procedure in the Methodology'],
  [/premija nelikvidnosti \+([\d.,]+) p\.b\./g, 'illiquidity premium of +$1 p.p.'],
  [/TTM podaci \(/g, 'TTM data ('],
  // M43-5: raspis traženog prinosa r u pretpostavkama (cijela klauzula s
  // capture grupama — bez word-level pravila koja bi razbila dulje rečenice)
  [/komponente traženog prinosa r = ([\d.,]+)%: nerizična stopa ([\d.,]+)% \+ β ([\d.,]+) × tržišna premija ([\d.,]+)% \+ premija rizika zemlje ([\d.,]+) p\.b\.( \+ premija nelikvidnosti ([\d.,]+) p\.b\.)?/g,
    (_m, r, rf, b, erp, crp, _illiqAll, illiq) =>
      `required-return components r = ${r}%: risk-free rate ${rf}% + β ${b} × market premium ${erp}% + country risk premium ${crp} p.p.`
      + (illiq ? ` + illiquidity premium ${illiq} p.p.` : '')],
  [/godišnji podatak/g, 'annual data point'],
  [/kratka serija \(rast\)/g, 'short series (growth)'],
  [/komponente r-a: rf /g, 'components of r: rf '],
  [/peer multipli \(/g, 'peer multiples ('],
  [/holding diskont ([\d.,]+)–([\d.,]+)%/g, 'holding discount of $1–$2%'],
  [/SOTP dijelovi na pretpostavljenim multiplama: /g, 'SOTP parts at assumed multiples: '],

  // ---- bank KPI: neobjavljene stavke ----
  [/U izvješću nisu objavljeni \(nema u bazi\): /g, 'Not published in the report (not in the database): '],
  [/NPL omjer/g, 'NPL ratio'],
  [/NPL pokrivenost/g, 'NPL coverage'],
  [/CET1 stopa/g, 'CET1 ratio'],
  [/Ukupna stopa kapitala/g, 'Total capital ratio'],

  // ---- SOTP / holding diskont / rizici ----
  [/IZMJERENI vlastiti P\/NAV/g, 'MEASURED own P/NAV'],
  [/: medijan ([\d.,]+) \(p25 /g, ': median $1 (p25 '],
  [/-> diskont /g, '-> discount '],
  [/\. serija M(\d+) \(/g, '. series M$1 ('],
  [/na KONZERVATIVNOM NAV proxyju \(neuvršteni dijelovi na placeholder multiplama, grupni neto dug konstantan\)/g,
    'on the CONSERVATIVE NAV proxy (unlisted parts at placeholder multiples, group net debt held constant)'],
  [/opažena PREMIJA se klampa na diskont ([\d.,]+) — premija se ne ugrađuje u fer/g,
    'the observed PREMIUM is clamped to a discount of $1 — a premium is not built into the fair value'],
  [/Tržište vrednuje uvrštene kćeri ([+\-][\d.,]+)% u odnosu na našu fer-procjenu; fer-zona matice koristi našu procjenu, pa razlika ostaje otvoreno pitanje tržišta\./g,
    "The market values the listed subsidiaries at $1% relative to our fair estimate; the parent's fair-value zone uses our estimate, so the difference remains an open question for the market."],
  [/Vrijednost i dividende matice ovise o društvima: /g,
    "The parent's value and dividends depend on these companies: "],
  [/KONČAR/g, 'KONCAR'],
  [/standalone \(ex-uvrštene kćeri\)/g, 'standalone (excl. listed subsidiaries)'],

  // ---- metrics / dividende ----
  [/per-share: ([A-Z]+) konsolidirane financije \/ dionice bez trezorskih; trž\.kap = Σ zadnji close klase × dionice klase/g,
    'per-share: $1 consolidated financials / shares excluding treasury; market cap = Σ latest class close × class shares'],
  [/zadnja isplata (FY\d{4})/g, 'last payment $1'],

  // ---- generička pravila (UVIJEK zadnja — specifičnija idu iznad) ----
  [/ nema u bazi/g, ' not in the database'],
  [/\bp\.b\./g, 'p.p.'],
  [/\bdo\b/g, 'to'],
]

export function tx(s, lang) {
  if (lang !== 'en' || s === null || s === undefined) return s
  if (Object.prototype.hasOwnProperty.call(DATA_TX, s)) return DATA_TX[s]
  let r = s
  for (const [re, sub] of PATTERNS) r = r.replace(re, sub)
  return r
}
