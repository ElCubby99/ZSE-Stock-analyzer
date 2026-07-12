import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GapCell, SECTOR_HR, SiteFooter, SiteHeader, useOverview } from './Shell.jsx'
import { num } from './format.js'

const COLS = [
  ['ticker', 'DIONICA', 'l'], ['sector', 'SEKTOR', 'l'], ['price', 'CIJENA €', 'r'],
  ['pe', 'P/E', 'r'], ['pb', 'P/B', 'r'], ['div_yield', 'PRINOS %', 'r'],
  ['gap', 'RASKORAK', 'l'],
]

export default function Screener() {
  const ov = useOverview()
  const nav = useNavigate()
  const [sk, setSk] = useState('gap'); const [dir, setDir] = useState(1)
  const [sec, setSec] = useState('Svi')
  useEffect(() => { document.title = 'Screener · Burzovni list' }, [])
  if (!ov) return <div className="shellpg"><SiteHeader /><div className="loading">učitavam…</div></div>
  const gap = (s) => (s.zone_low === null || s.zone_low === undefined || !s.price ? null
    : s.price > s.zone_high ? s.price / s.zone_high - 1
      : s.price < s.zone_low ? s.price / s.zone_low - 1 : 0)
  const sectors = ['Svi', ...Array.from(new Set(ov.stocks.map((s) => s.sector).filter(Boolean)))]
  let list = ov.stocks.filter((s) => sec === 'Svi' || s.sector === sec)
  list = [...list].sort((a, b) => {
    const av = sk === 'gap' ? gap(a) : a[sk]; const bv = sk === 'gap' ? gap(b) : b[sk]
    if (typeof av === 'string' || typeof bv === 'string') return String(av).localeCompare(String(bv)) * dir
    const an = av === null || av === undefined ? Infinity * dir : av
    const bn = bv === null || bv === undefined ? Infinity * dir : bv
    return (an - bn) * dir
  })
  const sort = (k) => () => { setDir(sk === k ? -dir : 1); setSk(k) }
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title">
          <h1>Screener</h1>
          <span>{list.length} klasa · klik na zaglavlje sortira · klik na redak otvara dionicu</span>
        </div>
        <div className="prof-chips" style={{ marginBottom: 18 }}>
          <span className="prof-klabel" style={{ margin: 0 }}>SEKTOR:</span>
          {sectors.map((c) => (
            <button key={c} className={`prof-chip ${sec === c ? 'on' : ''}`}
              onClick={() => setSec(c)}>{(SECTOR_HR[c] || c).toUpperCase()}</button>
          ))}
        </div>
        <div className="mk-scroll">
          <div className="scr-table">
            <div className="scr-hd">
              {COLS.map(([k, l, ta]) => (
                <button key={k} className={ta} onClick={sort(k)}>
                  {l}{sk === k ? (dir === 1 ? ' ↑' : ' ↓') : ''}
                </button>
              ))}
            </div>
            {list.map((s) => (
              <div className="scr-row" key={s.ticker} onClick={() => nav(`/dionica/${s.company}`)}>
                <span className="mk-name"><b>{s.ticker}</b><em>{s.name}</em>
                  {s.illiquid && <i className="mk-ill">ILIKV.</i>}</span>
                <span className="dim">{SECTOR_HR[s.sector] || s.sector || '—'}</span>
                <span className="r mono">{s.price === null ? '—' : num(s.price, 2)}</span>
                <span className="r mono dim">{s.pe === null || s.pe === undefined ? '—' : num(s.pe, 1)}</span>
                <span className="r mono dim">{s.pb === null || s.pb === undefined ? '—' : num(s.pb, 2)}</span>
                <span className="r mono dim">{s.div_yield ? num(s.div_yield * 100, 1) : '—'}</span>
                <GapCell s={s} />
              </div>
            ))}
            <div className="mk-legend">
              <span>RASKORAK = položaj tržišne cijene naspram fer-zone · negativno = ispod, pozitivno = iznad · n/p = analiza u obradi ili bez zone</span>
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
