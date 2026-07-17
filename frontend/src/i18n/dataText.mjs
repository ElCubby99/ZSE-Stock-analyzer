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

}

/* Pattern pravila za stringove s dinamičkim dijelovima (datumi, n=,
   popisi peera). Primjenjuju se redom NAKON promašaja exact mape. */
const PATTERNS = [
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
  [/\bdo\b/g, 'to'],
]

export function tx(s, lang) {
  if (lang !== 'en' || s === null || s === undefined) return s
  if (Object.prototype.hasOwnProperty.call(DATA_TX, s)) return DATA_TX[s]
  let r = s
  for (const [re, sub] of PATTERNS) r = r.replace(re, sub)
  return r
}
