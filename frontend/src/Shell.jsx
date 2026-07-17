import React, { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { num } from './format.js'
import { useConsent } from './consent.jsx'
import { useLang } from './i18n/LangContext.jsx'
import { pairPath } from './routes/registry.mjs'

/* App ljuska po dizajnu: logo + top-level nav + search; footer s MAR ogradom.
   M38: sve user-facing stringove daje i18n rječnik (useLang().t); navigacija
   i linkovi prate jezik rute (/en/...). Jezični switcher vodi na PAR
   trenutne stranice (pairPath iz registryja) — bez IP auto-redirecta. */

// SECTOR_HR živi u sectorLabels.mjs (dijele ga SPA i prerender)
export { SECTOR_HR } from './sectorLabels.mjs'
export { SECTOR_EN } from './sectorLabels.mjs'

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

const stockPath = (lang, c) => (lang === 'en'
  ? `/en/stock/${String(c).toLowerCase()}` : `/dionica/${String(c).toLowerCase()}`)

function Search() {
  const ov = useOverview()
  const nav = useNavigate()
  const { lang } = useLang()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  const hits = !q ? [] : (ov?.stocks || [])
    .filter((s) => (s.ticker + ' ' + s.name).toLowerCase().includes(q.toLowerCase()))
    .filter((s, i, a) => a.findIndex((x) => x.company === s.company) === i)
    .slice(0, 8)
  const go = (c) => { setQ(''); setOpen(false); nav(stockPath(lang, c)) }
  return (
    <div className="hdr-search" ref={box}>
      <input value={q} placeholder={lang === 'en' ? 'ticker or name…' : 'ticker ili ime…'}
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

/* M31: nav u klikabilne grupe; M38: grupe se grade po jeziku iz rječnika.
   EN v1 namjerno NEMA: Blog (ostaje HR), Alati (HR kalkulatori s HR pravnim
   sadržajem), Portfelj (login-gated HR UI) — vidi nalog M38 DIO 3. */
function navGroups(lang, t) {
  if (lang === 'en') {
    return [
      {
        label: t('nav.market').toUpperCase(),
        to: '/en',
        end: true,
        items: [
          { to: '/en', label: t('common.allStocks'), end: true },
          { to: '/en/screener', label: t('nav.screener') },
          { to: '/en/indices', label: t('nav.indices') },
          { to: '/en/bonds', label: t('nav.bonds') },
          { to: '/en/pension-funds', label: t('nav.pensionFunds') },
          { to: '/en/dividends', label: t('nav.dividends') },
          { to: '/en/comparison', label: t('nav.comparison') },
        ],
      },
      { label: t('nav.news').toUpperCase(), to: '/en/news' },
      { label: t('nav.methodology').toUpperCase(), to: '/en/methodology' },
    ]
  }
  return [
    {
      label: t('nav.market').toUpperCase(),
      to: '/',
      end: true,
      items: [
        { to: '/', label: t('common.allStocks'), end: true },
        { to: '/screener', label: t('nav.screener') },
        { to: '/indeksi', label: t('nav.indices') },
        { to: '/obveznice', label: t('nav.bonds') },
        { to: '/mirovinski-fondovi', label: t('nav.pensionFunds') },
        { to: '/dividende', label: t('nav.dividends') },
        { to: '/usporedba', label: t('nav.comparison') },
        { to: '/alati', label: t('nav.tools') },
      ],
    },
    { label: t('nav.portfolio').toUpperCase(), to: '/portfelj' },
    {
      label: t('nav.blog').toUpperCase(),
      to: '/blog',
      items: [
        { to: '/blog', label: t('nav.blog'), end: true },
        { to: '/vijesti', label: t('nav.news') },
      ],
    },
  ]
}

const groupActive = (g, pathname) => {
  const one = (it) => (it.to === '/' || it.to === '/en' ? pathname === it.to
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

function MobileNav({ last, groups, lang, t, onClose }) {
  const [expanded, setExpanded] = useState(groups[0]?.label)
  const { pathname } = useLocation()
  return (
    <nav className="hdr-mobile" aria-label={lang === 'en' ? 'Main menu' : 'Glavni izbornik'}>
      {groups.map((g) => (g.items ? (
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
      <NavLink to={stockPath(lang, last)}
        className={({ isActive }) => `hdr-mob-top${isActive ? ' active' : ''}`}
        onClick={onClose}>{lang === 'en' ? 'STOCK' : 'DIONICA'} · {last}</NavLink>
    </nav>
  )
}

/* M38: switcher vodi na PAR trenutne stranice; stranica bez para (blog,
   alati…) vodi na home drugog jezika. Izbor se pamti (bl_lang). */
function LangSwitch() {
  const { pathname } = useLocation()
  const { lang } = useLang()
  const other = lang === 'en' ? 'hr' : 'en'
  const target = pairPath(pathname) || (other === 'en' ? '/en' : '/')
  return (
    <NavLink to={target} className="hdr-lang" aria-label={other === 'en'
      ? 'Switch to English' : 'Prebaci na hrvatski'}>
      {other.toUpperCase()}
    </NavLink>
  )
}

export function SiteHeader() {
  const last = lastTicker()
  const { lang, t } = useLang()
  const [mobOpen, setMobOpen] = useState(false)
  const { pathname } = useLocation()
  useEffect(() => { setMobOpen(false) }, [pathname]) // navigacija zatvara panel
  const groups = navGroups(lang, t)
  return (
    <header className="hdr">
      <div className="hdr-in">
        <NavLink to={lang === 'en' ? '/en' : '/'} className="hdr-logo">
          <div className="hdr-mark">
            <div className="hdr-mark-band" /><div className="hdr-mark-line" />
          </div>
          <div>
            <div className="hdr-name">Burzovni list</div>
            <div className="hdr-tag">{lang === 'en'
              ? 'ZAGREB STOCK EXCHANGE ANALYTICS' : 'ZSE · ANALITIČKA PLATFORMA'}</div>
          </div>
        </NavLink>
        <nav className="hdr-nav">
          {groups.map((g) => <NavGroup g={g} key={g.label} />)}
          {/* kontekst trenutne dionice — nije dio glavnog menija */}
          <NavLink to={stockPath(lang, last)}
            className={({ isActive }) => (isActive ? 'on' : '')}>
            {lang === 'en' ? 'STOCK' : 'DIONICA'} · {last}
          </NavLink>
        </nav>
        <Search />
        <LangSwitch />
        <button type="button" className="hdr-burger"
          aria-label={lang === 'en' ? 'Menu' : 'Izbornik'}
          aria-expanded={mobOpen} onClick={() => setMobOpen((v) => !v)}>
          {mobOpen ? '✕' : '☰'}
        </button>
      </div>
      {mobOpen && <MobileNav last={last} groups={groups} lang={lang} t={t}
        onClose={() => setMobOpen(false)} />}
    </header>
  )
}

export function SiteFooter() {
  const { openSettings } = useConsent()
  const { lang, t } = useLang()
  const L = (hr, en) => (lang === 'en' ? en : hr)
  return (
    <footer className="ftr">
      <div className="ftr-in">
        <span className="ftr-main">{t('common.disclaimerLong')}</span>
        <span className="ftr-links">
          © 2026 Burzovni list ·{' '}
          <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a> ·{' '}
          <a href="/impressum">{t('footer.impressum')}</a> ·{' '}
          <a href={L('/metodologija', '/en/methodology')}>{t('common.methodology')}</a> ·{' '}
          <a href={L('/uvjeti-koristenja', '/en/terms')}>{t('footer.terms')}</a> ·{' '}
          <a href={L('/politika-privatnosti', '/en/privacy')}>{t('footer.privacy')}</a> ·{' '}
          <a href={L('/politika-kolacica', '/en/cookies')}>{t('footer.cookies')}</a> ·{' '}
          <button type="button" className="cc-inline-link" onClick={openSettings}>
            {t('footer.cookieSettings')}
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
          {t('common.freshness')}
        </span>
      </div>
    </footer>
  )
}

/* raskorak-motiv iz dizajna: pojas fer-zone + okomita crta cijene */
export function GapCell({ s }) {
  const { lang, t } = useLang()
  if (s.zone_low === null || s.zone_low === undefined || !s.price) {
    return <div className="mk-gap"><span className="np">{t('common.na')}</span></div>
  }
  const d0m = Math.min(s.zone_low, s.price); const d1m = Math.max(s.zone_high, s.price)
  const pad = (d1m - d0m) * 0.22 || d1m * 0.06
  const d0 = d0m - pad; const d1 = d1m + pad
  const P = (v) => Math.max(1.5, Math.min(98.5, ((v - d0) / (d1 - d0)) * 100))
  let lbl = lang === 'en' ? 'in zone' : 'u zoni'
  if (s.price > s.zone_high) {
    lbl = `+${num((s.price / s.zone_high - 1) * 100, 1)} % ${lang === 'en' ? 'above' : 'iznad'}`
  } else if (s.price < s.zone_low) {
    lbl = `−${num((1 - s.price / s.zone_low) * 100, 1)} % ${lang === 'en' ? 'below' : 'ispod'}`
  }
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
