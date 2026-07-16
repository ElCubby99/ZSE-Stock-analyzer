import React, { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { num } from './format.js'
import { useConsent } from './consent.jsx'

/* App ljuska po dizajnu: logo + top-level nav + search; footer s MAR ogradom.
   NE red svih tickera — do dionice se dolazi kroz Tržište/Screener/search. */

// SECTOR_HR živi u sectorLabels.mjs (dijele ga SPA i prerender)
export { SECTOR_HR } from './sectorLabels.mjs'

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
  const go = (c) => { setQ(''); setOpen(false); nav(`/dionica/${String(c).toLowerCase()}`) }
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

/* M31: nav u 3 klikabilne grupe. Klik na naziv grupe NAVIGIRA na prvu
   stavku (dropdown nije mrtav gumb); podmeni se na desktopu otvara hoverom
   (dosljedno za obje grupe), na mobilnom (<=768px) hamburger + accordion.
   Portfelj je namjerno samostalan — jedini login-gated dio.
   Rute se NE mijenjaju (registry/sitemap netaknuti — čista prezentacija). */
const NAV_GROUPS = [
  {
    label: 'TRŽIŠTE',
    to: '/',
    end: true,
    items: [
      { to: '/', label: 'Sve dionice', end: true },
      { to: '/screener', label: 'Screener' },
      { to: '/indeksi', label: 'Indeksi' },
      { to: '/obveznice', label: 'Obveznice' },
      { to: '/mirovinski-fondovi', label: 'Mirovinski fondovi' },
      { to: '/dividende', label: 'Dividende' },
      { to: '/usporedba', label: 'Usporedba' },
      { to: '/alati', label: 'Alati' },
    ],
  },
  { label: 'PORTFELJ', to: '/portfelj' },
  {
    label: 'BLOG',
    to: '/blog',
    items: [
      { to: '/blog', label: 'Blog', end: true },
      { to: '/vijesti', label: 'Vijesti' },
    ],
  },
]

const groupActive = (g, pathname) => {
  // '/' samo egzaktno; ostale rute i s podstranicama (/blog/<slug> -> BLOG)
  const one = (it) => (it.to === '/' ? pathname === '/'
    : pathname === it.to || pathname.startsWith(`${it.to}/`))
  return g.items ? g.items.some(one) : one(g)
}

function NavGroup({ g }) {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const active = groupActive(g, pathname)
  if (!g.items) {
    return <NavLink to={g.to} className={active ? 'on' : ''}>{g.label}</NavLink>
  }
  return (
    <div className={`hdr-group${open ? ' open' : ''}`}
      onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <NavLink to={g.to} end={g.end} className={active ? 'on' : ''}
        aria-haspopup="true" aria-expanded={open}
        onFocus={() => setOpen(true)}>
        {g.label}<span className="hdr-caret" aria-hidden="true">▾</span>
      </NavLink>
      <div className="hdr-dd" role="menu">
        {g.items.map((it) => (
          <NavLink key={it.label} to={it.to} end={it.end} role="menuitem"
            className={({ isActive }) => (isActive ? 'on' : '')}
            onClick={() => setOpen(false)}>{it.label}</NavLink>
        ))}
      </div>
    </div>
  )
}

function MobileNav({ last, onClose }) {
  const [expanded, setExpanded] = useState('TRŽIŠTE')
  const { pathname } = useLocation()
  return (
    <nav className="hdr-mobile" aria-label="Glavni izbornik">
      {NAV_GROUPS.map((g) => (g.items ? (
        <div key={g.label} className="hdr-mob-group">
          <button type="button" className={groupActive(g, pathname) ? 'on' : ''}
            aria-expanded={expanded === g.label}
            onClick={() => setExpanded(expanded === g.label ? null : g.label)}>
            {g.label}<span className="hdr-caret">{expanded === g.label ? '▴' : '▾'}</span>
          </button>
          {expanded === g.label && g.items.map((it) => (
            <NavLink key={it.label} to={it.to} end={it.end}
              className={({ isActive }) => `hdr-mob-sub${isActive ? ' active' : ''}`}
              onClick={onClose}>{it.label}</NavLink>
          ))}
        </div>
      ) : (
        <NavLink key={g.label} to={g.to}
          className={({ isActive }) => `hdr-mob-top${isActive ? ' active' : ''}`}
          onClick={onClose}>{g.label}</NavLink>
      )))}
      <NavLink to={`/dionica/${String(last).toLowerCase()}`}
        className={({ isActive }) => `hdr-mob-top${isActive ? ' active' : ''}`}
        onClick={onClose}>DIONICA · {last}</NavLink>
    </nav>
  )
}

export function SiteHeader() {
  const last = lastTicker()
  const [mobOpen, setMobOpen] = useState(false)
  const { pathname } = useLocation()
  useEffect(() => { setMobOpen(false) }, [pathname]) // navigacija zatvara panel
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
          {NAV_GROUPS.map((g) => <NavGroup g={g} key={g.label} />)}
          {/* kontekst trenutne dionice — nije dio glavnog menija */}
          <NavLink to={`/dionica/${String(last).toLowerCase()}`}
            className={({ isActive }) => (isActive ? 'on' : '')}>
            DIONICA · {last}
          </NavLink>
        </nav>
        <Search />
        <button type="button" className="hdr-burger" aria-label="Izbornik"
          aria-expanded={mobOpen} onClick={() => setMobOpen((v) => !v)}>
          {mobOpen ? '✕' : '☰'}
        </button>
      </div>
      {mobOpen && <MobileNav last={last} onClose={() => setMobOpen(false)} />}
    </header>
  )
}

export function SiteFooter() {
  const { openSettings } = useConsent()
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
          <a href="/uvjeti-koristenja">Uvjeti korištenja</a> ·{' '}
          <a href="/politika-privatnosti">Politika privatnosti</a> ·{' '}
          <a href="/politika-kolacica">Politika kolačića</a> ·{' '}
          <button type="button" className="cc-inline-link" onClick={openSettings}>
            Postavke kolačića
          </button> ·{' '}
          {/* M30: X handle iz env-a (VITE_X_HANDLE) — prazan = bez linka */}
          {(import.meta.env.VITE_X_HANDLE || '') && (
            <>
              <a href={`https://x.com/${String(import.meta.env.VITE_X_HANDLE).replace(/^@/, '')}`}
                target="_blank" rel="noopener noreferrer">
                X: @{String(import.meta.env.VITE_X_HANDLE).replace(/^@/, '')}
              </a> ·{' '}
            </>
          )}
          Izvor: ZSE službeni EOD · podaci se ažuriraju nakon zatvaranja burze
        </span>
      </div>
    </footer>
  )
}

/* raskorak-motiv iz dizajna: pojas fer-zone + okomita crta cijene */
export function GapCell({ s }) {
  /* v3 A: zona "u rekalibraciji" — naš vlastiti test (održiva dividenda)
     trenutačno pobija zonu pa je ne prikazujemo kao mjerodavnu */
  if (s.zone_status === 'u_rekalibraciji') {
    return (
      <div className="mk-gap">
        <span className="np" title={'fer-zona u rekalibraciji — unutarnji test modela (održiva dividenda) trenutačno pobija zonu; detalji na stranici dionice'}>
          u rekalibraciji
        </span>
      </div>
    )
  }
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
