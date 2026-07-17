/* M38: CENTRALNO formatiranje po jeziku — NIKAD ručno formatiranje u
   komponentama. Locale postavlja LangProvider (iz rute); prerender ga
   postavlja eksplicitno prije renderiranja svake jezične varijante.
   HR: 1.035.725,50 · 12,30 € · 16.7.2026.
   EN: 1,035,725.50 · €12.30 · 16 Jul 2026
   Sve funkcije toleriraju null -> "—" (ne izmišljamo). */

let LOCALE = 'hr'
const INTL = { hr: 'hr-HR', en: 'en-GB' }

export function setLocale(lang) { LOCALE = lang === 'en' ? 'en' : 'hr' }
export function getLocale() { return LOCALE }

const nf = (min, max) => new Intl.NumberFormat(INTL[LOCALE], {
  minimumFractionDigits: min, maximumFractionDigits: max,
})

export const dash = '—'

export function num(v, dec = 2) {
  if (v === null || v === undefined) return dash
  return nf(dec, dec).format(v)
}

export function eur(v, dec = 2) {
  if (v === null || v === undefined) return dash
  // HR konvencija: iznos pa simbol; EN konvencija: simbol pa iznos
  return LOCALE === 'en' ? `€${num(v, dec)}` : `${num(v, dec)} €`
}

export function meur(v, dec = 1) {
  if (v === null || v === undefined) return dash
  return LOCALE === 'en' ? `€${num(v / 1e6, dec)}M` : `${num(v / 1e6, dec)} M€`
}

export function pct(v, dec = 1) {
  if (v === null || v === undefined) return dash
  return `${num(v * 100, dec)}%`
}

const MJESECI_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/* ISO 'YYYY-MM-DD' -> lokalizirani datum. HR: 16.7.2026. · EN: 16 Jul 2026 */
export function fmtDate(iso) {
  if (!iso) return dash
  const s = String(iso).slice(0, 10)
  const [y, m, d] = s.split('-').map(Number)
  if (!y || !m || !d) return dash
  return LOCALE === 'en'
    ? `${d} ${MJESECI_EN[m - 1]} ${y}`
    : `${d}.${m}.${y}.`
}
