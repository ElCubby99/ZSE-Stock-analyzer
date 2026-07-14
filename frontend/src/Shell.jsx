import React, { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { num } from './format.js'

/* App ljuska po dizajnu: logo + top-level nav + search; footer s MAR ogradom.
   NE red svih tickera — do dionice se dolazi kroz Tržište/Screener/search. */

export const SECTOR_HR = {
  holding: 'Holding', insurance: 'Osiguranje', tourism: 'Turizam',
  consumer: 'Konzumeri', industrial: 'Industrija', bank: 'Banka',
  telecom: 'Telekomunikacije', technology: 'Tehnologija', energy: 'Energetika',
  shipping: 'Brodarstvo', aquaculture: 'Marikultura',
}

export function useOverview() {
  const [ov, setOv] = useState(null)
  useEffect(() => {
    fetch('/data/overview.json').then((r) => r.json()).then(setOv)
      .catch(() => setOv({ indices: [], stocks: [] }))
  }, [])
  return ov
}

export function lastTicker() {
  try { return localStorage.getItem('lastTicker') || 'ADRS' } catch { return 'ADRS' }
}

function Search() {
  const ov = useOverview()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  const hits = !q ? [] : (ov?.stocks || [])
    .filter((s) => (s.ticker + ' ' + s.name).toLowerCase().includes(q.toLowerCase()))
    .filter((s, i, a) => a.findIndex((x) => x.company === s.company) === i)
    .slice(0, 8)
  const go = (c) => { setQ(''); setOpen(false); nav(`/dionica/${c}`) }
  return (
    <div className="hdr-search" ref={box}>
      <input value={q} placeholder="ticker ili ime…"
        onChange={(e) => { setQ(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && hits.length) go(hits[0].company)
          if (e.key === 'Escape') { setQ(''); setOpen(false) }
        }} />
      {open && hits.length > 0 && (
        <div className="hdr-search-dd">
          {hits.map((s) => (
            <button key={s.ticker} onMouseDown={() => go(s.company)}>
              <b>{s.ticker}</b> <span>{s.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function SiteHeader() {
  const last = lastTicker()
  const items = [
    { to: '/', label: 'TRŽIŠTE', end: true },
    { to: '/screener', label: 'SCREENER' },
    { to: '/dividende', label: 'DIVIDENDE' },
    { to: '/portfelj', label: 'PORTFELJ' },
    { to: '/blog', label: 'BLOG' },
    { to: '/alati', label: 'ALATI' },
    { to: `/dionica/${last}`, label: `DIONICA · ${last}` },
  ]
  return (
    <header className="hdr">
      <div className="hdr-in">
        <NavLink to="/" className="hdr-logo">
          <div className="hdr-mark">
            <div className="hdr-mark-band" /><div className="hdr-mark-line" />
          </div>
          <div>
            <div className="hdr-name">Burzovni list</div>
            <div className="hdr-tag">ZSE · ANALITIČKA PLATFORMA</div>
          </div>
        </NavLink>
        <nav className="hdr-nav">
          {items.map((it) => (
            <NavLink key={it.label} to={it.to} end={it.end}
              className={({ isActive }) => (isActive ? 'on' : '')}>{it.label}</NavLink>
          ))}
        </nav>
        <Search />
      </div>
    </header>
  )
}

export function SiteFooter() {
  return (
    <footer className="ftr">
      <div className="ftr-in">
        <span className="ftr-main">
          Prikazani podaci, rasponi i fer-zone su informativni i analitički — ne
          predstavljaju investicijski savjet, preporuku ni poticaj na trgovanje.
          Vrijednosti ilikvidnih dionica su indikativne. Zaključak je uvijek vaš.
        </span>
        <span className="ftr-links">
          © 2026 Burzovni list ·{' '}
          <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a> ·{' '}
          <a href="/impressum">Impressum</a> ·{' '}
          <a href="/metodologija">Metodologija</a> ·{' '}
          Izvor: ZSE službeni EOD (dan zaostatka)
        </span>
      </div>
    </footer>
  )
}

/* raskorak-motiv iz dizajna: pojas fer-zone + okomita crta cijene */
export function GapCell({ s }) {
  if (s.zone_low === null || s.zone_low === undefined || !s.price) {
    return <div className="mk-gap"><span className="np">n/p</span></div>
  }
  const d0m = Math.min(s.zone_low, s.price); const d1m = Math.max(s.zone_high, s.price)
  const pad = (d1m - d0m) * 0.22 || d1m * 0.06
  const d0 = d0m - pad; const d1 = d1m + pad
  const P = (v) => Math.max(1.5, Math.min(98.5, ((v - d0) / (d1 - d0)) * 100))
  let lbl = 'u zoni'
  if (s.price > s.zone_high) lbl = `+${num((s.price / s.zone_high - 1) * 100, 1)} % iznad`
  else if (s.price < s.zone_low) lbl = `−${num((1 - s.price / s.zone_low) * 100, 1)} % ispod`
  const pref = s.ticker.endsWith('2')
  return (
    <div className="mk-gap">
      <div className="mk-band">
        <div className="mk-band-axis" />
        <div className="mk-band-zone" style={{ left: `${P(s.zone_low)}%`, width: `${P(s.zone_high) - P(s.zone_low)}%` }} />
        <div className="mk-band-tick" style={{ left: `${P(s.price)}%`, background: pref ? '#2F5D86' : '#9E2B25' }} />
      </div>
      <span className="mk-gap-lbl">{lbl}</span>
    </div>
  )
}

export const chg = (v) => (v === null || v === undefined ? '—'
  : `${v > 0 ? '+' : v < 0 ? '−' : '±'}${num(Math.abs(v) * 100, 2)} %`)
export const chgCol = (v) => (v > 0 ? '#1F6E5A' : v < 0 ? '#9E2B25' : 'rgba(38,46,51,0.55)')
