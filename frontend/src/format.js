// hr-HR formatiranje; sve prikazne funkcije toleriraju null -> "—" (ne izmišljamo).
const nf = (min, max) => new Intl.NumberFormat('hr-HR', {
  minimumFractionDigits: min, maximumFractionDigits: max,
})

export const dash = '—'

export function num(v, dec = 2) {
  if (v === null || v === undefined) return dash
  return nf(dec, dec).format(v)
}

export function eur(v, dec = 2) {
  if (v === null || v === undefined) return dash
  return `${num(v, dec)} €`
}

export function meur(v, dec = 1) {
  if (v === null || v === undefined) return dash
  return `${num(v / 1e6, dec)} M€`
}

export function pct(v, dec = 1) {
  if (v === null || v === undefined) return dash
  return `${num(v * 100, dec)}%`
}
