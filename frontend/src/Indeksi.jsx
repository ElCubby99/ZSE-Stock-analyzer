import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { num } from './format.js'

/* M-IDX: /indeksi (kartice svih ZSE indeksa + temperatura tržišta) i
   /indeks/<slug> (graf + sastavnice s težinama). Podaci: /data/indeksi.json
   (build_indeksi.py — službene ZSE vrijednosti + IndexComposition težine).
   MAR-safe: činjenični prikazi, temperatura je naša metrika s ogradom. */

const OX = '#9E2B25'
const RANGES = [
  { key: '1M', days: 31 }, { key: '3M', days: 92 },
  { key: '1G', days: 366 }, { key: 'MAX', days: 9999 },
]

export function useIndeksi() {
  const [d, setD] = useState(null)
  useEffect(() => {
    fetch('/data/indeksi.json').then((r) => r.json()).then(setD)
      .catch(() => setD({ indices: [], temperature: null }))
  }, [])
  return d
}

const chg = (v) => (v === null || v === undefined ? 'n/p'
  : `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 2)} %`)
const chgCol = (v) => (v === null || v === undefined ? 'inherit'
  : v >= 0 ? '#1F6E5A' : OX)

function fmtHr(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${Number(d)}.${Number(m)}.${y}.`
}

/* Ista vizualna gramatika kao PriceChart sa stranice dionice (linija,
   hairline grid, mono oznake) — generalizirano za bilo koju seriju. */
export function IndexChart({ series, label }) {
  const [range, setRange] = useState('1G')
  const rc = RANGES.find((r) => r.key === range) || RANGES[2]
  const clipped = useMemo(() => {
    if (!series?.length) return []
    const last = series[series.length - 1].date
    const cut = new Date(last)
    cut.setDate(cut.getDate() - rc.days)
    const cutIso = cut.toISOString().slice(0, 10)
    const pts = series.filter((p) => p.date >= cutIso)
    return pts.length > 1 ? pts : series
  }, [series, rc.days])
  if (!clipped.length) return <div className="prof-empty">nema serije u bazi</div>

  const W = 760; const H = 230; const pT = 12; const pB = 26; const pL = 10; const pR = 66
  const vals = clipped.map((p) => p.value)
  let vMin = Math.min(...vals); let vMax = Math.max(...vals)
  const vPad = (vMax - vMin) * 0.07 || vMax * 0.03
  vMin -= vPad; vMax += vPad
  const n = clipped.length - 1 || 1
  const yF = (v) => pT + ((vMax - v) / (vMax - vMin)) * (H - pT - pB)
  const xF = (i) => pL + (i / n) * (W - pL - pR)
  const poly = clipped.map((p, i) => `${xF(i).toFixed(1)},${yF(p.value).toFixed(1)}`).join(' ')
  const last = clipped[clipped.length - 1]
  const gy = [0.25, 0.5, 0.75].map((f) => (pT + (H - pT - pB) * f).toFixed(1))
  const x2 = W - pR
  return (
    <div className="prof-panel">
      <div className="prof-panel-head">
        <span className="prof-klabel">{label}</span>
        <div className="prof-chips">
          {RANGES.map((r) => (
            <button key={r.key} className={`prof-chip ${range === r.key ? 'on' : ''}`}
              onClick={() => setRange(r.key)}>{r.key}</button>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}
        role="img" aria-label={`Kretanje ${label}`}>
        {gy.map((y) => <line key={y} x1={pL} x2={x2} y1={y} y2={y} stroke="rgba(38,46,51,0.09)" />)}
        <polyline points={poly} fill="none" stroke={OX} strokeWidth="1.6"
          strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={xF(clipped.length - 1)} cy={yF(last.value)} r="3.5" fill={OX} />
        <text x={x2 + 8} y={yF(last.value)} dy="4" fill={OX}
          fontFamily="IBM Plex Mono" fontSize="11" fontWeight="600">{num(last.value, 2)}</text>
        <text x={pL + 4} y="20" fill="rgba(38,46,51,0.45)" fontFamily="IBM Plex Mono" fontSize="10">{num(vMax, 2)}</text>
        <text x={pL + 4} y={H - 12} fill="rgba(38,46,51,0.45)" fontFamily="IBM Plex Mono" fontSize="10">{num(vMin, 2)}</text>
      </svg>
      <div className="prof-panel-foot">
        <span>{fmtHr(clipped[0].date)} – {fmtHr(last.date)}</span>
        <span className="prof-legend">službene ZSE vrijednosti (EOD)</span>
      </div>
    </div>
  )
}

function Sparkline({ series }) {
  const pts = (series || []).slice(-60)
  if (pts.length < 2) return null
  const W = 140; const H = 36
  const vals = pts.map((p) => p.value)
  const vMin = Math.min(...vals); const vMax = Math.max(...vals)
  const span = (vMax - vMin) || 1
  const poly = pts.map((p, i) =>
    `${((i / (pts.length - 1)) * W).toFixed(1)},${(H - 3 - ((p.value - vMin) / span) * (H - 6)).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} aria-hidden="true">
      <polyline points={poly} fill="none" stroke={OX} strokeWidth="1.3" />
    </svg>
  )
}

/* Temperatura tržišta — stacked bar u gramatici fer-zona prikaza */
export function TemperatureBar({ t }) {
  if (!t || !t.total) return null
  const seg = (n, col) => (n > 0
    ? <div style={{ flex: n, background: col, minWidth: 2 }} /> : null)
  const pctTxt = (n) => `${Math.round((n / t.total) * 100)} %`
  return (
    <div className="idx-temp">
      <div className="sec-label">Temperatura tržišta · sastavnice {t.index}-a naspram fer-zona</div>
      <div className="idx-temp-bar" role="img"
        aria-label={`${t.above} iznad, ${t.inside} u zoni, ${t.below} ispod fer-zone`}>
        {seg(t.above, 'rgba(158,43,37,0.75)')}
        {seg(t.inside, 'rgba(31,110,90,0.55)')}
        {seg(t.below, 'rgba(47,93,134,0.65)')}
        {seg(t.np, 'rgba(38,46,51,0.15)')}
      </div>
      <div className="idx-temp-leg">
        <span><i style={{ background: 'rgba(158,43,37,0.75)' }} /> iznad zone: {t.above} ({pctTxt(t.above)})</span>
        <span><i style={{ background: 'rgba(31,110,90,0.55)' }} /> u zoni: {t.inside} ({pctTxt(t.inside)})</span>
        <span><i style={{ background: 'rgba(47,93,134,0.65)' }} /> ispod zone: {t.below} ({pctTxt(t.below)})</span>
        {t.np > 0 && <span><i style={{ background: 'rgba(38,46,51,0.15)' }} /> n/p: {t.np}</span>}
      </div>
      <p className="fund-src">{t.note}.</p>
    </div>
  )
}

export function IndeksiIndex() {
  const d = useIndeksi()
  useEffect(() => { document.title = 'Indeksi Zagrebačke burze · Burzovni list' }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>Indeksi Zagrebačke burze</h1>
          <span>službene vrijednosti · ažurira se nakon zatvaranja trgovine (16:00)</span></div>
        {!d ? <div className="loading">učitavam…</div> : (
          <>
            <TemperatureBar t={d.temperature} />
            <div className="idx-grid">
              {d.indices.map((ix) => (
                <Link to={`/indeks/${ix.slug}`} key={ix.slug} className="idx-card">
                  <div className="prof-klabel">{ix.name}</div>
                  <div className="mk-idx-v">{num(ix.value, 2)}</div>
                  <Sparkline series={ix.series} />
                  <div className="idx-card-rows mono">
                    <span style={{ color: chgCol(ix.change_pct) }}>dan {chg(ix.change_pct)}</span>
                    <span style={{ color: chgCol(ix.ytd_pct) }}>YTD {chg(ix.ytd_pct)}</span>
                    <span style={{ color: chgCol(ix.y1_pct) }}>1g {chg(ix.y1_pct)}</span>
                  </div>
                  <div className="fund-src">{ix.description}</div>
                </Link>
              ))}
            </div>
            <div className="disc" style={{ marginTop: 28 }}>
              Informativni prikaz službenih vrijednosti indeksa — nije
              investicijski savjet ni preporuka.
            </div>
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}

export function IndeksDetail() {
  const { slug } = useParams()
  const d = useIndeksi()
  const ix = d?.indices?.find((x) => x.slug === slug)
  useEffect(() => {
    if (ix) document.title = `${ix.name} danas — vrijednost, sastav i povijest · Burzovni list`
  }, [ix])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        {!d ? <div className="loading">učitavam…</div>
          : !ix ? (
            <section><div className="mk-title"><h1>Indeks nije pronađen</h1></div>
              <p className="imp-p"><Link to="/indeksi">← svi indeksi</Link></p></section>
          ) : (
            <>
              <div className="mk-title">
                <h1>{ix.name} — vrijednost, sastav i povijest</h1>
                <span>{ix.description} · službeni EOD za {fmtHr(ix.date)}</span>
              </div>
              <div className="mk-idx" style={{ marginBottom: 16 }}>
                <div className="mk-idx-c">
                  <div className="prof-klabel">VRIJEDNOST</div>
                  <div className="mk-idx-v">{num(ix.value, 2)}</div>
                  <div className="mono" style={{ color: chgCol(ix.change_pct), fontSize: 12 }}>{chg(ix.change_pct)}</div>
                </div>
                <div className="mk-idx-c"><div className="prof-klabel">YTD</div>
                  <div className="mk-idx-v" style={{ color: chgCol(ix.ytd_pct) }}>{chg(ix.ytd_pct)}</div></div>
                <div className="mk-idx-c"><div className="prof-klabel">1 GODINA</div>
                  <div className="mk-idx-v" style={{ color: chgCol(ix.y1_pct) }}>{chg(ix.y1_pct)}</div></div>
              </div>
              <IndexChart series={ix.series} label={`${ix.name} · VRIJEDNOST`} />
              {ix.constituents?.length > 0 && (
                <section style={{ marginTop: 24 }}>
                  <div className="sec-label">Sastavnice ({ix.constituents.length})
                    {ix.constituents[0]?.as_of ? ` · stanje ${fmtHr(ix.constituents[0].as_of)}` : ''}</div>
                  <table>
                    <thead><tr><th>Ticker</th><th>Naziv</th><th className="r">Težina</th></tr></thead>
                    <tbody>
                      {ix.constituents.map((c) => (
                        <tr key={c.ticker}>
                          <td>{c.company
                            ? <Link to={`/dionica/${c.company.toLowerCase()}`}>{c.ticker}</Link>
                            : c.ticker}</td>
                          <td>{c.name}</td>
                          <td className="r mono">{c.weight_pct !== null && c.weight_pct !== undefined
                            ? `${num(c.weight_pct, 2)} %` : 'n/p'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="fund-src">Izvor sastavnica i težina: ZSE (IndexComposition).</p>
                </section>
              )}
              <div className="disc" style={{ marginTop: 28 }}>
                Informativni prikaz — nije investicijski savjet ni preporuka.
              </div>
            </>
          )}
      </main>
      <SiteFooter />
    </div>
  )
}
