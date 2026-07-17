/* Jedan izvor istine za hrvatske nazive sektora — koristi ga SPA (Shell.jsx)
   i prerender (statične tablice u SSG HTML-u). Čisti .mjs bez JSX-a. */
export const SECTOR_HR = {
  holding: 'Holding', insurance: 'Osiguranje', tourism: 'Turizam',
  consumer: 'Konzumeri', industrial: 'Industrija', bank: 'Banka',
  telecom: 'Telekomunikacije', technology: 'Tehnologija', energy: 'Energetika',
  shipping: 'Brodarstvo', aquaculture: 'Marikultura', fund: 'Fond (ZAIF)',
  transport: 'Promet', construction: 'Graditeljstvo', real_estate: 'Nekretnine',
  other: 'Ostalo',
}

/* M38: engleski nazivi sektora — isti ključevi kao SECTOR_HR */
export const SECTOR_EN = {
  holding: 'Holding', insurance: 'Insurance', tourism: 'Tourism',
  consumer: 'Consumer', industrial: 'Industrials', bank: 'Bank',
  telecom: 'Telecommunications', technology: 'Technology', energy: 'Energy',
  shipping: 'Shipping', aquaculture: 'Aquaculture', fund: 'Fund (closed-end)',
  transport: 'Transport', construction: 'Construction', real_estate: 'Real estate',
  other: 'Other',
}

export const sectorLabel = (key, lang) =>
  ((lang === 'en' ? SECTOR_EN : SECTOR_HR)[key]) || key || null
