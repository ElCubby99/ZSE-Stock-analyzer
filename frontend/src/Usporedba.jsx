import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GapCell, SiteFooter, SiteHeader, useOverview } from './Shell.jsx'
import { dash, num, pct } from './format.js'
import { useLang } from './i18n/LangContext.jsx'
import { sectorLabel } from './sectorLabels.mjs'

/* Z5: /usporedba — screener svih klasa s multiplima + side-by-side
   usporedba 2-5 odabranih dionica. Podaci: overview.json (isti export kao
   Tržište/Screener); n/p ostaje prazno, ništa se ne procjenjuje. */

const COLS = [
  ['ticker', 'mkt.col.stock', 'l'],
  ['sector', 'common.sector', 'l'],
  ['price', 'scr.col.priceEur', 'r'],
  ['market_cap', 'cmp.mcap', 'r'],
  ['pe', 'P/E', 'r'],
  ['pb', 'P/B', 'r'],
  ['ev_ebitda', 'EV/EBITDA', 'r'],
  ['earnings_yield', 'EARN. YLD', 'r'],
  ['div_yield', 'div.yield', 'r'],
  ['payout', 'PAYOUT', 'r'],
  ['gap', 'mkt.col.gap', 'l'],
  ['turnover', 'mkt.col.turnover', 'r'],
]

const gapVal = (s) => {
  if (!s.price || s.zone_low === null || s.zone_low === undefined) return null
  const mid = (s.zone_low + s.zone_high) / 2
  return mid ? s.price / mid - 1 : null
}

function MiniZone({ s }) {
  if (s.zone_low === null || s.zone_low === undefined || !s.price) {
    return <span className="np">fer-zona n/p</span>
  }
  return <GapCell s={s} />
}

function CompareCards({ picked, stocks, t }) {
  const sel = stocks.filter((s) => picked.has(s.ticker))
  if (sel.length < 2) return null
  const P = [
    [t('scr.col.priceEur'), (s) => (s.price === null ? dash : num(s.price, 2))],
    [t('cmp.mcap'), (s) => (s.market_cap ? `${num(s.market_cap / 1e6, 0)} M€` : dash)],
    ['P/E', (s) => (s.pe ? num(s.pe, 1) : dash)],
    ['P/B', (s) => (s.pb ? num(s.pb, 2) : dash)],
    ['EV/EBITDA', (s) => (s.is_financial ? `${t('common.na')} (fin.)` : s.ev_ebitda ? num(s.ev_ebitda, 1) : dash)],
    ['Earnings yield', (s) => (s.earnings_yield ? pct(s.earnings_yield, 1) : dash)],
    [t('div.yield'), (s) => (s.div_yield ? pct(s.div_yield, 2) : dash)],
    ['Payout', (s) => (s.payout ? pct(s.payout, 0) : dash)],
    [`${t('mkt.col.turnover')}/d`, (s) => (s.turnover ? num(s.turnover, 0) : dash)],
  ]
  return (
    <section id="usporedi">
      <div className="sec-label">{t('nav.comparison')} ({sel.length})</div>
      <div className="cmp-cards">
        {sel.map((s) => (
          <div className="cmp-card" key={s.ticker}>
            <div className="cmp-card-h">
              <b>{s.ticker}</b>
              <span className="fund-src">{s.name}</span>
              {s.illiquid && <span className="flag">{t('mkt.illiq')}</span>}
            </div>
            {P.map(([k, f]) => (
              <div className="cmp-card-row" key={k}>
                <span>{k}</span><span className="mono">{f(s)}</span>
              </div>
            ))}
            <div className="cmp-card-row"><span>{t('stock.fairZone')}</span></div>
            <MiniZone s={s} />
          </div>
        ))}
      </div>
      <div className="subnote">{t('cmp.cardNote')}</div>
    </section>
  )
}

export default function Usporedba() {
  const ov = useOverview()
  const { lang, t } = useLang()
  const nav = useNavigate()
  const [sk, setSk] = useState('ticker')
  const [dir, setDir] = useState(1)
  const [sector, setSector] = useState('svi')
  const [q, setQ] = useState('')
  const [picked, setPicked] = useState(() => new Set())

  useEffect(() => { document.title = `${t('cmp.title')} | Burzovni list` }, [lang])

  const stocks = ov?.stocks || []
  const sectors = useMemo(
    () => [...new Set(stocks.map((s) => s.sector).filter(Boolean))].sort(), [stocks])

  const rows = useMemo(() => {
    let list = stocks
    if (sector !== 'svi') list = list.filter((s) => s.sector === sector)
    if (q) {
      const ql = q.toLowerCase()
      list = list.filter((s) => (s.ticker + ' ' + s.name).toLowerCase().includes(ql))
    }
    const val = (s) => (sk === 'gap' ? gapVal(s) : sk === 'sector'
      ? (sectorLabel(s.sector, 'hr') || s.sector || '') : s[sk])
    return [...list].sort((a, b) => {
      const av = val(a); const bv = val(b)
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av ?? '').localeCompare(String(bv ?? '')) * dir
      }
      const an = av === null || av === undefined ? Infinity * dir : av
      const bn = bv === null || bv === undefined ? Infinity * dir : bv
      return (an - bn) * dir
    })
  }, [stocks, sector, q, sk, dir])

  const sort = (k) => () => {
    setDir(sk === k ? -dir : (k === 'ticker' || k === 'sector') ? 1 : -1)
    setSk(k)
  }
  const toggle = (t) => setPicked((p) => {
    const n = new Set(p)
    if (n.has(t)) n.delete(t)
    else if (n.size < 5) n.add(t)
    return n
  })

  if (!ov) {
    return (
      <div className="shellpg"><SiteHeader />
        <main className="wrap-wide"><div className="loading">{t('common.loading')}</div></main>
        <SiteFooter /></div>
    )
  }
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title">
          <h1>{t('cmp.title')}</h1>
          <span>P/E, P/B, EV/EBITDA — {t('cmp.subtitle')}</span>
        </div>

        <div className="prof-chips" style={{ margin: '10px 0' }}>
          <button className={sector === 'svi' ? 'on' : ''}
            onClick={() => setSector('svi')}>{t('scr.allSectors')}</button>
          {sectors.map((s) => (
            <button key={s} className={sector === s ? 'on' : ''}
              onClick={() => setSector(s)}>{(sectorLabel(s, lang) || s).toUpperCase()}</button>
          ))}
          <input className="usp-search" placeholder={t('cmp.searchPh')}
            value={q} onChange={(e) => setQ(e.target.value)} />
        </div>

        {picked.size >= 2 && (
          <div className="subnote" style={{ margin: '4px 0 8px' }}>
            {t('cmp.picked')} {picked.size}/5 — <a href="#usporedi">{t('cmp.jump')}</a>
          </div>
        )}

        <div className="mk-scroll">
          <div className="usp-table">
            <div className="mk-hd">
              <span title="odaberi 2-5 za usporedbu">✓</span>
              {COLS.map(([k, key, ta]) => (
                <button key={k} className={ta === 'r' ? 'r' : ''} onClick={sort(k)}>
                  {(key.includes('.') && !key.includes(' ') ? t(key) : key).toUpperCase()}{sk === k ? (dir === 1 ? ' ↑' : ' ↓') : ''}
                </button>
              ))}
            </div>
            {rows.map((s) => (
              <div className="mk-row" key={s.ticker}
                onClick={() => nav(`/dionica/${String(s.company).toLowerCase()}`)}>
                <span onClick={(e) => { e.stopPropagation(); toggle(s.ticker) }}>
                  <input type="checkbox" readOnly checked={picked.has(s.ticker)} />
                </span>
                <span className="mk-name"><b>{s.ticker}</b><em>{s.name}</em>
                  {s.illiquid && <span className="flag" style={{ marginLeft: 6 }}>ILIKV.</span>}</span>
                <span>{sectorLabel(s.sector, lang) || dash}</span>
                <span className="r mono">{s.price === null ? dash : num(s.price, 2)}</span>
                <span className="r mono">{s.market_cap ? `${num(s.market_cap / 1e6, 0)} M` : dash}</span>
                <span className="r mono">{s.pe ? num(s.pe, 1) : dash}</span>
                <span className="r mono">{s.pb ? num(s.pb, 2) : dash}</span>
                <span className="r mono">{s.is_financial ? <i className="np">n/p</i>
                  : s.ev_ebitda ? num(s.ev_ebitda, 1) : dash}</span>
                <span className="r mono">{s.earnings_yield ? pct(s.earnings_yield, 1) : dash}</span>
                <span className="r mono">{s.div_yield ? pct(s.div_yield, 2) : dash}</span>
                <span className="r mono">{s.payout ? pct(s.payout, 0) : dash}</span>
                <span><GapCell s={s} /></span>
                <span className="r mono">{s.turnover ? num(s.turnover, 0) : dash}</span>
              </div>
            ))}
          </div>
        </div>

        <CompareCards picked={picked} stocks={stocks} t={t} />

        <div className="disc">
          <b>{t('common.notAdvice')}</b>{' '}
          {t('cmp.disc')}
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
