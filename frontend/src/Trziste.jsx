import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GapCell, SiteFooter, SiteHeader, chg, chgCol, useOverview } from './Shell.jsx'
import { num } from './format.js'

const eur0 = (v) => (v === null || v === undefined ? '—' : num(v, 2))

function Movers({ title, list, nav }) {
  return (
    <div>
      <h2 className="mk-h2">{title}</h2>
      <div className="mk-movers">
        {list.map((s) => (
          <div key={s.ticker} className="mk-mrow" onClick={() => nav(`/dionica/${s.company}`)}>
            <b>{s.ticker}</b>
            <span className="mk-nm">{s.name}</span>
            <span className="mono">{eur0(s.price)}</span>
            <span className="mono" style={{ color: chgCol(s.change_pct) }}>{chg(s.change_pct)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Trziste() {
  const ov = useOverview()
  const nav = useNavigate()
  const [key, setKey] = useState('vol')
  useEffect(() => { document.title = 'Tržište · Burzovni list' }, [])
  if (!ov) return <div className="wrap"><SiteHeader /><div className="loading">učitavam…</div></div>
  // zadnji trgovinski dan na tržištu (max datum EOD zapisa) — dobitnici i
  // gubitnici DANA smiju biti samo dionice stvarno trgovane TAJ dan (ustajala
  // promjena od prije nije "promjena dana")
  const latestDate = ov.stocks.reduce((m, s) => (s.date && s.date > m ? s.date : m), '')
  const fmtDate = latestDate
    ? `${latestDate.slice(8, 10)}.${latestDate.slice(5, 7)}.${latestDate.slice(0, 4)}.` : null
  const withChg = ov.stocks.filter((s) => s.change_pct !== null
    && s.change_pct !== undefined && s.date === latestDate)
  const gainers = [...withChg].sort((a, b) => b.change_pct - a.change_pct).slice(0, 4)
  const losers = [...withChg].sort((a, b) => a.change_pct - b.change_pct).slice(0, 4)
  const list = [...ov.stocks].sort((a, b) => key === 'vol' ? (b.turnover || 0) - (a.turnover || 0)
    : key === 'chg' ? (b.change_pct || -9) - (a.change_pct || -9) : a.ticker.localeCompare(b.ticker))
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title">
          <h1>Tržište danas</h1>
          <span>Zagrebačka burza · službeni EOD{fmtDate ? ` za ${fmtDate}` : ''} (dan zaostatka)</span>
        </div>
        <div className="mk-idx">
          {ov.indices.length ? ov.indices.map((ix) => (
            <div className="mk-idx-c" key={ix.name}>
              <div className="prof-klabel">{ix.name}</div>
              <div className="mk-idx-v">{num(ix.value, 2)}</div>
              <div className="mono" style={{ color: chgCol(ix.change_pct), fontSize: 12 }}>{chg(ix.change_pct)}</div>
            </div>
          )) : <div className="mk-idx-c"><div className="prof-klabel">INDEKSI</div><div className="np">nema u bazi</div></div>}
          <div className="mk-idx-c">
            <div className="prof-klabel">PRAĆENE DIONICE</div>
            <div className="mk-idx-v">{ov.stocks.length}</div>
            <div className="mono" style={{ fontSize: 12, color: 'rgba(38,46,51,0.6)' }}>klasa u sustavu</div>
          </div>
        </div>
        <div className="mk-movers-grid">
          <Movers title={`Najveći dobitnici${fmtDate ? ` · ${fmtDate}` : ''}`} list={gainers} nav={nav} />
          <Movers title={`Najveći gubitnici${fmtDate ? ` · ${fmtDate}` : ''}`} list={losers} nav={nav} />
        </div>
        <div className="subnote" style={{ marginTop: 6 }}>
          Promjene se odnose na trgovinski dan {fmtDate || '—'}; dionice koje taj dan
          nisu trgovane nisu u dobitnicima/gubitnicima (njihova zadnja cijena je starija).
        </div>
        <div className="mk-title2">
          <h2 className="mk-h2">Sve dionice</h2>
          <div className="prof-chips">
            <span className="prof-klabel" style={{ margin: 0 }}>SORTIRAJ:</span>
            {[['vol', 'PROMET'], ['chg', 'PROMJENA'], ['name', 'TICKER']].map(([k, l]) => (
              <button key={k} className={`prof-chip ${key === k ? 'on' : ''}`} onClick={() => setKey(k)}>{l}</button>
            ))}
          </div>
        </div>
        <div className="mk-scroll">
          <div className="mk-table">
            <div className="mk-hd">
              <span>DIONICA</span><span className="r">ZADNJA €</span><span className="r">PROMJENA</span>
              <span className="r">PROMET €</span><span className="r">FER-ZONA €</span><span>RASKORAK</span>
            </div>
            {list.map((s) => (
              <div className="mk-row" key={s.ticker} onClick={() => nav(`/dionica/${s.company}`)}>
                <span className="mk-name"><b>{s.ticker}</b><em>{s.name}</em>
                  {s.illiquid && <i className="mk-ill">ILIKV.</i>}</span>
                <span className="r mono">{eur0(s.price)}</span>
                <span className="r mono" style={{ color: chgCol(s.change_pct) }}>{chg(s.change_pct)}</span>
                <span className="r mono dim">{s.turnover ? num(s.turnover, 0) : '—'}</span>
                <span className="r mono pine">{s.zone_low !== null && s.zone_low !== undefined
                  ? `${num(s.zone_low, 0)}–${num(s.zone_high, 0)}` : '—'}</span>
                <GapCell s={s} />
              </div>
            ))}
            <div className="mk-legend">
              <span><i className="mk-sw-zone" />fer-zona (naša procjena)</span>
              <span><i className="mk-sw-tick" style={{ background: '#9E2B25' }} />tržišna cijena</span>
              <span><i className="mk-sw-tick" style={{ background: '#2F5D86' }} />povlaštena dionica</span>
              <span>ILIKV. = rijetke transakcije, cijena indikativna · n/p = analiza u obradi</span>
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
