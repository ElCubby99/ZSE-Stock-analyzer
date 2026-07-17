/* M38: rječnik prijevoda — JEDAN izvor istine za sve user-facing stringove.
   Svaki ključ nosi OBA jezika ({hr, en}) pa nedostajući prijevod ne može
   proći tiho. Financijski pojmovi MORAJU pratiti docs/glossary_hr_en.md.
   Pravilo (CLAUDE.md): novi user-facing string ide OVDJE, nikad hardkodiran
   u komponentu; lint test (tests/test_i18n.py) hvata prekršaje. */

export const STR = {
  /* ---------- zajedničko ---------- */
  'common.na': { hr: 'n/p', en: 'n/a' },
  'common.dash': { hr: '—', en: '—' },
  'common.loading': { hr: 'učitavam…', en: 'loading…' },
  'common.source': { hr: 'Izvor', en: 'Source' },
  'common.sourceDoc': { hr: 'izvorni dokument', en: 'source document' },
  'common.notAdvice': {
    hr: 'Informativno — nije investicijski savjet ni preporuka.',
    en: 'For information only — not investment advice or a recommendation.',
  },
  'common.disclaimerLong': {
    hr: 'Prikazani podaci, rasponi i fer-zone su informativni i analitički — ne predstavljaju investicijski savjet, preporuku ni poticaj na trgovanje. Vrijednosti ilikvidnih dionica su indikativne. Zaključak je uvijek vaš.',
    en: 'The data, ranges and fair-value zones shown are informational and analytical — they are not investment advice, a recommendation, or an inducement to trade. Values of illiquid stocks are indicative. The conclusion is always yours.',
  },
  'common.freshness': {
    hr: 'Izvor: ZSE službeni EOD · podaci se ažuriraju nakon zatvaranja burze',
    en: 'Source: ZSE official end-of-day data · updated after market close',
  },
  'common.backToStock': { hr: 'profil dionice', en: 'stock profile' },
  'common.methodology': { hr: 'Metodologija', en: 'Methodology' },
  'common.download': { hr: 'Preuzmi CSV', en: 'Download CSV' },
  'common.sector': { hr: 'Sektor', en: 'Sector' },
  'common.price': { hr: 'Cijena', en: 'Price' },
  'common.company': { hr: 'Firma', en: 'Company' },
  'common.ticker': { hr: 'Ticker', en: 'Ticker' },
  'common.date': { hr: 'Datum', en: 'Date' },
  'common.status': { hr: 'Status', en: 'Status' },
  'common.error': { hr: 'Greška', en: 'Error' },
  'common.allStocks': { hr: 'Sve dionice', en: 'All stocks' },
  'common.home': { hr: 'Naslovnica', en: 'Home' },
  'common.stocks': { hr: 'Dionice', en: 'Stocks' },

  /* ---------- navigacija (Shell) ---------- */
  'nav.market': { hr: 'Tržište', en: 'Market' },
  'nav.screener': { hr: 'Screener', en: 'Screener' },
  'nav.comparison': { hr: 'Usporedba', en: 'Comparison' },
  'nav.dividends': { hr: 'Dividende', en: 'Dividends' },
  'nav.indices': { hr: 'Indeksi', en: 'Indices' },
  'nav.bonds': { hr: 'Obveznice', en: 'Bonds' },
  'nav.pensionFunds': { hr: 'Mirovinski fondovi', en: 'Pension funds' },
  'nav.news': { hr: 'Vijesti', en: 'News' },
  'nav.blog': { hr: 'Blog', en: 'Blog' },
  'nav.tools': { hr: 'Alati', en: 'Tools' },
  'nav.methodology': { hr: 'Metodologija', en: 'Methodology' },
  'nav.portfolio': { hr: 'Portfelj', en: 'Portfolio' },
  'nav.groupData': { hr: 'Podaci', en: 'Data' },
  'nav.groupAnalysis': { hr: 'Analiza', en: 'Analysis' },
  'nav.groupMore': { hr: 'Više', en: 'More' },
  'brand.tagline': {
    hr: 'analiza dionica Zagrebačke burze',
    en: 'Zagreb Stock Exchange Analytics',
  },

  /* ---------- footer ---------- */
  'footer.impressum': { hr: 'Impressum', en: 'Impressum' },
  'footer.terms': { hr: 'Uvjeti korištenja', en: 'Terms of Use' },
  'footer.privacy': { hr: 'Politika privatnosti', en: 'Privacy Policy' },
  'footer.cookies': { hr: 'Politika kolačića', en: 'Cookie Policy' },
  'footer.cookieSettings': { hr: 'Postavke kolačića', en: 'Cookie settings' },

  /* ---------- tabovi stranice dionice ---------- */
  'stock.tab.overview': { hr: 'PREGLED', en: 'OVERVIEW' },
  'stock.tab.valuation': { hr: 'ANALIZA VRIJEDNOSTI', en: 'VALUATION ANALYSIS' },
  'stock.tab.indicators': { hr: 'KLJUČNI POKAZATELJI', en: 'KEY INDICATORS' },
  'stock.tab.comparison': { hr: 'USPOREDBA', en: 'COMPARISON' },
  'stock.tab.reports': { hr: 'IZVJEŠTAJI', en: 'REPORTS' },
  'stock.tab.shareholders': { hr: 'DIONIČARI', en: 'SHAREHOLDERS' },
  'stock.tab.news': { hr: 'NOVOSTI', en: 'NEWS' },
  'stock.tab.financials': { hr: 'FINANCIJE', en: 'FINANCIALS' },
  'stock.analysisTitle': { hr: 'analiza dionice', en: 'stock analysis' },
  'stock.lastPrice': { hr: 'Zadnja cijena', en: 'Last price' },
  'stock.fairZone': { hr: 'fer-zona', en: 'fair-value zone' },
  'stock.priceVsZone': { hr: 'Cijena vs zona', en: 'Price vs zone' },
  'stock.inZone': { hr: 'u fer-zoni', en: 'in fair-value zone' },
  'stock.aboveZone': { hr: 'iznad fer-zone', en: 'above fair-value zone' },
  'stock.belowZone': { hr: 'ispod fer-zone', en: 'below fair-value zone' },
  'stock.zseEur': { hr: 'Zagrebačka burza · EUR', en: 'Zagreb Stock Exchange · EUR' },
  'stock.unknownSector': { hr: 'sektor nepoznat', en: 'sector unknown' },

  /* ---------- financije (M37) ---------- */
  'fin.title': { hr: 'Financijski izvještaji', en: 'Financial statements' },
  'fin.income': { hr: 'Dobit i gubitak', en: 'Income statement' },
  'fin.balance': { hr: 'Financijski položaj', en: 'Balance sheet' },
  'fin.cashflow': { hr: 'Novčani tok', en: 'Cash flow' },
  'fin.annual': { hr: 'Godišnje', en: 'Annual' },
  'fin.quarterly': { hr: 'Kvartalno', en: 'Quarterly' },
  'fin.consolidated': { hr: 'konsolidirano', en: 'consolidated' },
  'fin.separate': { hr: 'nekonsolidirano', en: 'separate' },
  'fin.view': { hr: 'Prikaz', en: 'View' },
  'fin.cumulative': {
    hr: 'kumulativi od početka godine (kako su objavljeni)',
    en: 'year-to-date cumulatives (as reported)',
  },
  'fin.unitThousands': { hr: 'u tisućama EUR', en: 'EUR thousands' },
  'fin.unitMillions': { hr: 'u milijunima EUR', en: 'EUR millions' },
  'fin.hrkBadge': { hr: 'preračunato iz HRK', en: 'converted from HRK' },
  'fin.restatedBadge': {
    hr: 'korigirano u kasnijem izvješću — klik za raniju vrijednost',
    en: 'restated in a later report — click for the earlier value',
  },
  'fin.earlierPublication': { hr: 'Ranija objava', en: 'Earlier publication' },
  'fin.prevQ4': { hr: '4Q kumulativ', en: '4Q cumulative' },
  'fin.item': { hr: 'Stavka', en: 'Line item' },
  'fin.notInDb': { hr: 'za ovaj prikaz nije u bazi', en: 'is not in our database for this view' },
  'fin.missing': { hr: 'Nije u bazi', en: 'Not in our database' },
  'fin.noData': {
    hr: 'Za ovu dionicu još nemamo ekstrahirane izvještaje u bazi.',
    en: 'We have not yet extracted financial statements for this stock.',
  },
  'fin.docsNote': {
    hr: 'popis dokumenata: kartica IZVJEŠTAJI na profilu',
    en: 'document list: REPORTS tab on the stock profile',
  },
  'fin.schemaNote': {
    hr: 'Stavke prema našoj standardiziranoj shemi ekstrakcije (kanonska nomenklatura) — originalne oznake nalaze se u izvornom dokumentu na koji vodi poveznica u zaglavlju svake kolone. Periodi prije 2023. preračunati su iz HRK po fiksnom tečaju 7,5345 HRK/EUR. Kvartalni prikaz prikazuje kumulative od početka godine, kako su objavljeni. Prazno polje (—) znači da stavka za taj period nije ekstrahirana — nikad se ne prikazuje nula umjesto nepoznate vrijednosti.',
    en: 'Line items follow our standardized extraction schema (canonical nomenclature) — the original labels are in the source document linked in each column header. Periods before 2023 are converted from HRK at the fixed rate of 7.5345 HRK/EUR. The quarterly view shows year-to-date cumulatives, as reported. An empty cell (—) means the item was not extracted for that period — a zero is never shown in place of an unknown value.',
  },
  'fin.restateNote': {
    hr: 'Oznaka K uz vrijednost: korigirano u kasnijem izvješću — klik otvara raniju objavljenu vrijednost. Izvedene veličine (TTM, marže, po dionici) nalaze se na kartici Ključni pokazatelji na',
    en: 'The K mark next to a value: restated in a later report — click to see the earlier published value. Derived figures (TTM, margins, per-share) live on the Key indicators tab of the',
  },
  'fin.publication': { hr: 'objava', en: 'published' },
  'fin.sourceDocTitle': { hr: 'Izvorni dokument', en: 'Source document' },

  /* ---------- stavke izvještaja (as-reported shema) ---------- */
  'li.revenue': { hr: 'Poslovni prihodi', en: 'Operating revenue' },
  'li.other_operating_income': { hr: 'Ostali poslovni prihodi', en: 'Other operating income' },
  'li.operating_expenses': { hr: 'Poslovni rashodi', en: 'Operating expenses' },
  'li.material_costs': { hr: 'Materijalni troškovi', en: 'Material costs' },
  'li.depreciation_amortization': { hr: 'Amortizacija', en: 'Depreciation and amortization' },
  'li.ebit': { hr: 'Operativna dobit (EBIT)', en: 'Operating profit (EBIT)' },
  'li.net_financial_result': { hr: 'Neto financijski rezultat', en: 'Net financial result' },
  'li.interest_expense': { hr: 'Rashodi od kamata', en: 'Interest expense' },
  'li.net_interest_income': { hr: 'Neto kamatni prihod', en: 'Net interest income' },
  'li.net_fee_income': { hr: 'Neto prihod od naknada i provizija', en: 'Net fee and commission income' },
  'li.total_operating_income': { hr: 'Ukupni operativni prihod', en: 'Total operating income' },
  'li.loan_loss_provisions': { hr: 'Rezervacije za kreditne gubitke', en: 'Loan loss provisions' },
  'li.dividend_income_from_subsidiaries': { hr: 'Prihod od dividendi ovisnih društava', en: 'Dividend income from subsidiaries' },
  'li.pretax_income': { hr: 'Dobit prije poreza', en: 'Pre-tax profit' },
  'li.income_tax': { hr: 'Porez na dobit', en: 'Income tax' },
  'li.net_income': { hr: 'Neto dobit razdoblja', en: 'Net profit for the period' },
  'li.net_income_parent': { hr: 'pripada vlasnicima matice', en: 'attributable to owners of the parent' },
  'li.net_income_minority': { hr: 'pripada manjinskim udjelima', en: 'attributable to non-controlling interests' },
  'li.total_assets': { hr: 'Ukupna imovina', en: 'Total assets' },
  'li.current_assets': { hr: 'Kratkotrajna imovina', en: 'Current assets' },
  'li.inventories': { hr: 'Zalihe', en: 'Inventories' },
  'li.trade_receivables': { hr: 'Potraživanja od kupaca', en: 'Trade receivables' },
  'li.short_term_fin_assets': { hr: 'Kratkoročna financijska imovina', en: 'Short-term financial assets' },
  'li.cash_and_equivalents': { hr: 'Novac i novčani ekvivalenti', en: 'Cash and cash equivalents' },
  'li.loans_to_customers': { hr: 'Krediti i potraživanja od klijenata', en: 'Loans and receivables from customers' },
  'li.total_equity': { hr: 'Ukupni kapital i rezerve', en: 'Total equity and reserves' },
  'li.equity_parent': { hr: 'pripada vlasnicima matice', en: 'attributable to owners of the parent' },
  'li.minority_interests': { hr: 'manjinski udjeli', en: 'non-controlling interests' },
  'li.retained_earnings': { hr: 'zadržana dobit', en: 'retained earnings' },
  'li.current_liabilities': { hr: 'Kratkoročne obveze', en: 'Current liabilities' },
  'li.trade_payables': { hr: 'Obveze prema dobavljačima', en: 'Trade payables' },
  'li.debt_short': { hr: 'Kratkoročne financijske obveze (dug)', en: 'Short-term financial liabilities (debt)' },
  'li.debt_long': { hr: 'Dugoročne financijske obveze (dug)', en: 'Long-term financial liabilities (debt)' },
  'li.deposits_from_customers': { hr: 'Depoziti klijenata', en: 'Customer deposits' },
  'li.operating_cf': { hr: 'Novčani tok iz poslovnih aktivnosti', en: 'Cash flow from operating activities' },
  'li.investing_cf': { hr: 'Novčani tok iz investicijskih aktivnosti', en: 'Cash flow from investing activities' },
  'li.capex': { hr: 'Kapitalna ulaganja (capex)', en: 'Capital expenditure (capex)' },
  'li.financing_cf': { hr: 'Novčani tok iz financijskih aktivnosti', en: 'Cash flow from financing activities' },

  /* ---------- dividende ---------- */
  'div.title': { hr: 'Kalendar dividendi Zagrebačke burze', en: 'ZSE dividend calendar' },
  'div.status.paid': { hr: 'isplaćena', en: 'paid' },
  'div.status.upcoming': { hr: 'nadolazeća', en: 'upcoming' },
  'div.status.proposed': { hr: 'prijedlog', en: 'proposed' },
  'div.amountPerShare': { hr: 'Iznos po dionici', en: 'Amount per share' },
  'div.exDate': { hr: 'Ex-datum', en: 'Ex-date' },
  'div.paymentDate': { hr: 'Isplata', en: 'Payment date' },
  'div.fy': { hr: 'FG', en: 'FY' },
  'div.yield': { hr: 'Prinos', en: 'Yield' },

  /* ---------- screener / naslovnica / usporedba ---------- */
  'scr.title': { hr: 'Screener dionica Zagrebačke burze', en: 'Croatian stocks screener' },
  'home.title': { hr: 'Analiza dionica Zagrebačke burze', en: 'Zagreb Stock Exchange stock analysis' },
  'cmp.title': { hr: 'Usporedba dionica Zagrebačke burze', en: 'Compare Zagreb Stock Exchange stocks' },
  'idx.title': { hr: 'Indeksi Zagrebačke burze', en: 'Zagreb Stock Exchange indices' },
  'bond.title': { hr: 'Obveznice na Zagrebačkoj burzi', en: 'Bonds on the Zagreb Stock Exchange' },
  'fund.title': { hr: 'Mirovinski fondovi (OMF)', en: 'Mandatory pension funds' },
  'news.title': { hr: 'Vijesti', en: 'News' },
  'mkt.temperature': { hr: 'Temperatura tržišta', en: 'Market temperature' },

  /* ---------- kategorije vijesti ---------- */
  'newscat.novo_izvjesce': { hr: 'NOVO IZVJEŠĆE', en: 'NEW REPORT' },
  'newscat.dividenda': { hr: 'DIVIDENDA', en: 'DIVIDEND' },
  'newscat.promjena_cijene': { hr: 'CIJENA', en: 'PRICE' },
  'newscat.opce': { hr: 'OPĆE', en: 'GENERAL' },

  /* ---------- jezični switcher ---------- */
  'lang.switchToEn': { hr: 'EN', en: 'EN' },
  'lang.switchToHr': { hr: 'HR', en: 'HR' },
  'lang.blogNote': {
    hr: 'Blog je dostupan na hrvatskom.',
    en: 'The blog is currently available in Croatian.',
  },
}

/* t('key', 'en') -> prijevod; nepoznat ključ pada GLASNO u devu (konzola),
   a u produkciji vraća ključ (vidljivo, ali ne ruši stranicu). */
export function t(key, lang = 'hr') {
  const e = STR[key]
  if (!e) {
    if (typeof console !== 'undefined') console.error(`[i18n] nepoznat ključ: ${key}`)
    return key
  }
  return e[lang] || e.hr
}
