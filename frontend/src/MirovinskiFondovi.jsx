import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { fmtDate, meur, num } from './format.js'
import { useLang } from './i18n/LangContext.jsx'

/* M-FOND: /mirovinski-fondovi — vrijednosti obračunskih jedinica OMF-ova
   (A/B/C) i Mirex (izvor HANFA, MJESEČNI ritam) + sinergija s našim
   podacima: ZSE dionice u čijim se top-10 popisima pojavljuju OMF-ovi.
   BEZ rangiranja fondova (abecedni redoslijed) — činjenični prikaz.
   M-FOND2: graf usporedbe (fondovi međusobno + Mirex) na standardnim
   rasponima; normirano na 100 na početku raspona (usporedivo kretanje,
   ne apsolutne razine — jedinice i indeks nemaju istu skalu). */

export function useFondovi() {
  const [d, setD] = useState(null)
  useEffect(() => {
    fetch('/data/fondovi.json').then((r) => r.json()).then(setD)
      .catch(() => setD({ units: [], mirex: [], synergy: [], units_available: false }))
  }, [])
  return d
}

const pct = (v, na) => (v === null || v === undefined ? na
  : `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 2)} %`)

/* ---------- M-FOND2: graf usporedbe ---------- */

const CHART_COLORS = ['#9E2B25', '#2F5D86', '#1F6E5A', '#B0762B', '#6E4E9E',
  '#C05C79', '#3E8E8C', '#7A6A54']
const RANGES = [['ytd', 'fund.rg.ytd'], ['y1', 'fund.rg.y1'], ['y3', 'fund.rg.y3'],
  ['y5', 'fund.rg.y5'], ['y10', 'fund.rg.y10'], ['max', 'fund.rg.max']]
const RANGE_YEARS = { y1: 1, y3: 3, y5: 5, y10: 10 }

const seriesLabel = (s) => (s.kind === 'mirex' ? `Mirex ${s.category}` : `${s.fund} ${s.category}`)

export function FundChart() {
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [range, setRange] = useState('y1')
  const [sel, setSel] = useState(null)
  useEffect(() => {
    fetch('/data/fondovi_series.json')
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((d) => {
        if (d?.series?.length) {
          const def = d.series.filter((s) => s.category === 'B').map((s) => s.id)
          setSel(new Set(def.length ? def : d.series.map((s) => s.id)))
          setData(d)
        } else setData(false)
      })
      .catch(() => setData(false))
  }, [])
  const toggle = (id) => setSel((old) => {
    const n = new Set(old)
    if (n.has(id)) { if (n.size > 1) n.delete(id) } else n.add(id)
    return n
  })

  if (data === false) {
    return (
      <section style={{ marginTop: 14 }}>
        <div className="sec-label">{t('fund.chartTitle')}</div>
        <div className="subnote">{t('fund.chartEmpty')}</div>
      </section>
    )
  }
  if (!data || !sel) return <div className="loading">{t('common.loading')}</div>

  const asOf = data.as_of || ''
  let cutIso = null
  if (range === 'ytd') cutIso = `${asOf.slice(0, 4)}-01-01`
  else if (RANGE_YEARS[range]) {
    const d0 = new Date(asOf)
    d0.setDate(d0.getDate() - Math.round(365.25 * RANGE_YEARS[range]))
    cutIso = d0.toISOString().slice(0, 10)
  }

  /* usporedivost: serije nemaju isti početak (A/C kategorije od 2014.,
     B i Mirex B od 2002.) — normiranje na VLASTITI početak dalo bi
     neusporedive prinose, pa se sve odabrane serije režu i normiraju od
     ZAJEDNIČKOG početka (najkasniji prvi datum među odabranima) */
  const pick = (s) => ((range === 'ytd' || range === 'y1') && s.d?.length > 1 ? s.d : s.m)
  const selected = data.series.filter((s) => sel.has(s.id))
  const firstDates = selected.map((s) => pick(s)[0]?.[0]).filter(Boolean)
  const commonStart = firstDates.length
    ? firstDates.reduce((a, b) => (a > b ? a : b)) : null
  let effCut = cutIso
  let clipped = false
  if (commonStart && (!effCut || commonStart > effCut)) {
    clipped = effCut ? true : new Set(firstDates).size > 1
    effCut = commonStart
  }

  const lines = []
  selected.forEach((s) => {
    const src = pick(s)
    const pts = effCut ? src.filter((p) => p[0] >= effCut) : src
    if (pts.length < 2) return
    const base = pts[0][1]
    lines.push({ s, pts: pts.map((p) => ({ t: Date.parse(p[0]), v: (p[1] / base) * 100 })) })
  })

  const W = 760; const H = 300; const pT = 12; const pB = 24; const pL = 10; const pR = 56
  let body = null
  if (lines.length) {
    const allT = lines.flatMap((l) => [l.pts[0].t, l.pts[l.pts.length - 1].t])
    const tMin = Math.min(...allT); const tMax = Math.max(...allT)
    const allV = lines.flatMap((l) => l.pts.map((p) => p.v))
    let vMin = Math.min(...allV); let vMax = Math.max(...allV)
    const vPad = (vMax - vMin) * 0.06 || 2
    vMin -= vPad; vMax += vPad
    const xF = (tv) => pL + ((tv - tMin) / (tMax - tMin || 1)) * (W - pL - pR)
    const yF = (v) => pT + ((vMax - v) / (vMax - vMin)) * (H - pT - pB)
    const x2 = W - pR
    const gy = [0.25, 0.5, 0.75].map((f) => (pT + (H - pT - pB) * f).toFixed(1))
    body = (
      <>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}
          role="img" aria-label={t('fund.chartTitle')}>
          {gy.map((y) => <line key={y} x1={pL} x2={x2} y1={y} y2={y} stroke="rgba(38,46,51,0.09)" />)}
          {vMin < 100 && vMax > 100 && (
            <line x1={pL} x2={x2} y1={yF(100)} y2={yF(100)} stroke="rgba(38,46,51,0.30)"
              strokeDasharray="2 3" />
          )}
          {lines.map((l, i) => (
            <polyline key={l.s.id} fill="none"
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={l.s.kind === 'mirex' ? 1.4 : 1.7}
              strokeDasharray={l.s.kind === 'mirex' ? '6 4' : undefined}
              points={l.pts.map((p) => `${xF(p.t).toFixed(1)},${yF(p.v).toFixed(1)}`).join(' ')} />
          ))}
          {vMin < 100 && vMax > 100 && (
            <text x={x2 + 4} y={yF(100) + 3.5} fontFamily="IBM Plex Mono" fontSize="10"
              fill="rgba(38,46,51,0.55)">100</text>
          )}
          <text x={x2 + 4} y={pT + 4} fontFamily="IBM Plex Mono" fontSize="10"
            fill="rgba(38,46,51,0.55)">{num(vMax, 0)}</text>
          <text x={x2 + 4} y={H - pB} fontFamily="IBM Plex Mono" fontSize="10"
            fill="rgba(38,46,51,0.55)">{num(vMin, 0)}</text>
          <text x={pL} y={H - 6} fontFamily="IBM Plex Mono" fontSize="10"
            fill="rgba(38,46,51,0.55)">{fmtDate(new Date(tMin).toISOString().slice(0, 10))}</text>
          <text x={x2} y={H - 6} textAnchor="end" fontFamily="IBM Plex Mono" fontSize="10"
            fill="rgba(38,46,51,0.55)">{fmtDate(new Date(tMax).toISOString().slice(0, 10))}</text>
        </svg>
        <div className="fnd-leg">
          {lines.map((l, i) => {
            const ret = l.pts[l.pts.length - 1].v - 100
            return (
              <span key={l.s.id} className="fnd-leg-item">
                <i className="swatch" style={{
                  background: l.s.kind === 'mirex' ? 'transparent' : CHART_COLORS[i % CHART_COLORS.length],
                  border: l.s.kind === 'mirex'
                    ? `2px dashed ${CHART_COLORS[i % CHART_COLORS.length]}` : 'none',
                }} />
                {seriesLabel(l.s)}{' '}
                <b className="mono">{ret >= 0 ? '+' : '−'}{num(Math.abs(ret), 1)} %</b>
              </span>
            )
          })}
        </div>
      </>
    )
  } else {
    body = <div className="subnote">{t('fund.chartEmpty')}</div>
  }

  return (
    <section style={{ marginTop: 14 }}>
      <div className="prof-panel">
        <div className="prof-panel-head">
          <span className="prof-klabel">{t('fund.chartTitle')}</span>
          <div className="prof-chips">
            {RANGES.map(([k, key]) => (
              <button key={k} className={`prof-chip ${range === k ? 'on' : ''}`}
                onClick={() => setRange(k)}>{t(key)}</button>
            ))}
          </div>
        </div>
        <div className="fnd-sel">
          <span className="fund-src">{t('fund.chartSeries')}:</span>
          {['A', 'B', 'C'].map((cat) => (
            <div className="fnd-selrow" key={cat}>
              <span className="fnd-selcat">{cat}</span>
              {data.series.filter((s) => s.category === cat).map((s) => (
                <button key={s.id} className={`prof-chip ${sel.has(s.id) ? 'on' : ''}`}
                  onClick={() => toggle(s.id)}>{seriesLabel(s)}</button>
              ))}
            </div>
          ))}
        </div>
        {body}
        <div className="subnote" style={{ marginTop: 8 }}>
          {clipped && <b>{t('fund.chartCommon')} {fmtDate(effCut)}. </b>}
          {t('fund.chartRebase')}
        </div>
      </div>
    </section>
  )
}

export default function MirovinskiFondovi() {
  const d = useFondovi()
  const { lang, t } = useLang()
  useEffect(() => {
    document.title = `${t('fund.docTitle')} · Burzovni list`
  }, [lang])
  const na = t('common.na')
  const byTicker = useMemo(() => {
    const m = new Map()
    for (const s of d?.synergy || []) {
      if (!m.has(s.ticker)) m.set(s.ticker, { name: s.company_name, as_of: s.as_of, funds: [] })
      m.get(s.ticker).funds.push(s)
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [d])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>{t('fund.pageTitle')}</h1>
          <span>{t('fund.subtitle')}</span></div>
        {!d ? <div className="loading">{t('common.loading')}</div> : (
          <>
            <FundChart />
            {['A', 'B', 'C'].map((cat) => (
              <section key={cat} style={{ marginTop: 14 }}>
                <div className="sec-label">{t('fund.category')} {cat}</div>
                <div className="mk-scroll">
                <table>
                  <thead><tr><th>{t('fund.fund')}</th><th className="num">{t('fund.unit')}</th>
                    <th className="num">YTD</th><th className="num">{t('fund.y1')}</th>
                    <th className="num">{t('fund.y3')}</th><th className="num">{t('fund.y5')}</th>
                    <th className="num">{t('fund.y10')}</th>
                    <th>{t('fund.date')}</th></tr></thead>
                  <tbody>
                    {d.units.filter((u) => u.category === cat).map((u) => (
                      <tr key={u.fund}>
                        <td>{u.slug
                          ? <Link to={lang === 'en'
                            ? `/en/pension-fund/${u.slug}` : `/mirovinski-fond/${u.slug}`}>
                            <b>{u.fund} OMF</b></Link>
                          : <b>{u.fund} OMF</b>} — {t('fund.catLabel')} {cat}</td>
                        <td className="num">{u.unit_value !== null && u.unit_value !== undefined
                          ? num(u.unit_value, 4) : <span className="np">{t('fund.awaitingImport')}</span>}</td>
                        <td className="num">{pct(u.ytd, na)}</td>
                        <td className="num">{pct(u.y1, na)}</td>
                        <td className="num">{pct(u.y3, na)}</td>
                        <td className="num">{pct(u.y5, na)}</td>
                        <td className="num">{pct(u.y10, na)}</td>
                        <td className="fund-src">{fmtDate(u.value_date)}</td>
                      </tr>
                    ))}
                    {(() => {
                      const mx = d.mirex.find((m) => m.category === cat)
                      return (
                        <tr className="sotp-total" key="mirex">
                          <td>Mirex {cat} ({t('fund.compare')})</td>
                          <td className="num">{mx?.value !== null && mx?.value !== undefined
                            ? num(mx.value, 4) : <span className="np">{t('fund.awaitingImport')}</span>}</td>
                          <td className="num">{pct(mx?.ytd, na)}</td>
                          <td className="num">{pct(mx?.y1, na)}</td>
                          <td className="num">{pct(mx?.y3, na)}</td>
                          <td className="num">{pct(mx?.y5, na)}</td>
                          <td className="num">{pct(mx?.y10, na)}</td>
                          <td className="fund-src">{fmtDate(mx?.value_date)}</td>
                        </tr>
                      )
                    })()}
                  </tbody>
                </table>
                </div>
              </section>
            ))}
            {!d.units_available && (
              <div className="subnote" style={{ marginTop: 8 }}>
                {t('fund.firstImportNote')}
              </div>
            )}
            <section style={{ marginTop: 22 }}>
              <div className="sec-label">{t('fund.synergyTitle')}
                {byTicker[0]?.[1]?.as_of ? ` · ${t('fund.snapshot')} ${fmtDate(byTicker[0][1].as_of)}` : ''}</div>
              {byTicker.length ? (
                <table>
                  <thead><tr><th>{t('fund.stock')}</th><th>{t('fund.fundCat')}</th>
                    <th className="num">{t('fund.share')}</th></tr></thead>
                  <tbody>
                    {byTicker.map(([ticker, info]) => (
                      <tr key={ticker}>
                        <td><Link to={lang === 'en'
                          ? `/en/stock/${ticker.toLowerCase()}`
                          : `/dionica/${ticker.toLowerCase()}`}><b>{ticker}</b></Link>{' '}
                          <span className="basis">{info.name}</span></td>
                        <td>{info.funds.map((f) => `${f.fund} (${f.category})`).join(', ')}</td>
                        <td className="num">{num(info.funds.reduce((a, f) => a + (f.pct || 0), 0), 2)} %</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="subnote">{t('fund.noPositions')}</div>}
              <p className="fund-src">{t('fund.synergySrc')}</p>
            </section>
            <div className="disc" style={{ marginTop: 24 }}>
              {t('fund.disc')}
            </div>
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}

/* M-FOND3: /mirovinski-fond/<slug> — zasebna stranica pojedinog OMF-a
   (obitelj + kategorija). Prikazuje osnovne podatke, obračunsku jedinicu i
   prinose (iz povijesti jedinica), imovinu pod upravljanjem (HANFA neto
   imovina — pojavljuje se nakon prvog mjesečnog uvoza) i ZSE dionice u
   kojima je fond među top 10 dioničara (iz naših snapshota). Podaci se
   filtriraju po slugu iz istog /data/fondovi.json — bez novog izvora. */
export function FondDetail() {
  const { slug } = useParams()
  const d = useFondovi()
  const { lang, t } = useLang()
  const na = t('common.na')
  const unit = d?.units?.find((u) => u.slug === slug)
  const holdings = useMemo(
    () => (d?.synergy || []).filter((s) => s.slug === slug)
      .sort((a, b) => (b.pct || 0) - (a.pct || 0)),
    [d, slug],
  )
  useEffect(() => {
    if (unit) document.title = `${unit.fund} OMF ${unit.category} · Burzovni list`
  }, [unit, lang])
  const catNote = unit ? t(`fund.category.${unit.category}`) : ''
  const aum = unit?.aum
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        {!d ? <div className="loading">{t('common.loading')}</div>
          : !unit ? (
            <section><div className="mk-title"><h1>{t('fund.notFound')}</h1></div>
              <p className="imp-p"><Link to={lang === 'en' ? '/en/pension-funds' : '/mirovinski-fondovi'}>
                {t('fund.backToFunds')}</Link></p></section>
          ) : (
            <>
              <p className="fund-src" style={{ marginBottom: 4 }}>
                <Link to={lang === 'en' ? '/en/pension-funds' : '/mirovinski-fondovi'}>
                  {t('fund.backToFunds')}</Link></p>
              <div className="mk-title">
                <h1>{unit.fund} OMF — {t('fund.category')} {unit.category}</h1>
                <span>{t('fund.detailTitle')}</span>
              </div>

              <section style={{ marginTop: 8 }}>
                <div className="sec-label">{t('fund.overview')}</div>
                <table>
                  <tbody>
                    <tr><td>{t('fund.category')}</td>
                      <td><b>{unit.category}</b> — {catNote}</td></tr>
                    <tr><td>{t('fund.unit')}</td>
                      <td className="mono">{unit.unit_value !== null && unit.unit_value !== undefined
                        ? `${num(unit.unit_value, 4)} €` : <span className="np">{t('fund.awaitingImport')}</span>}
                        {unit.value_date ? <span className="fund-src"> · {fmtDate(unit.value_date)}</span> : null}</td></tr>
                    <tr><td>{t('fund.aum')}</td>
                      <td className="mono">{aum?.net_assets_eur
                        ? meur(aum.net_assets_eur, 1) : <span className="np">{t('fund.awaitingImport')}</span>}
                        {aum?.value_date ? <span className="fund-src"> · {fmtDate(aum.value_date)}</span> : null}</td></tr>
                    {aum?.members ? (
                      <tr><td>{t('fund.members')}</td>
                        <td className="mono">{num(aum.members, 0)}</td></tr>
                    ) : null}
                  </tbody>
                </table>
                <p className="fund-src" style={{ marginTop: 6 }}>{t('fund.aumWhy')}</p>
              </section>

              <section style={{ marginTop: 22 }}>
                <div className="sec-label">{t('fund.returnsTitle')}</div>
                <div className="mk-scroll">
                <table>
                  <thead><tr><th className="num">YTD</th><th className="num">{t('fund.y1')}</th>
                    <th className="num">{t('fund.y3')}</th><th className="num">{t('fund.y5')}</th>
                    <th className="num">{t('fund.y10')}</th></tr></thead>
                  <tbody>
                    <tr>
                      <td className="num">{pct(unit.ytd, na)}</td>
                      <td className="num">{pct(unit.y1, na)}</td>
                      <td className="num">{pct(unit.y3, na)}</td>
                      <td className="num">{pct(unit.y5, na)}</td>
                      <td className="num">{pct(unit.y10, na)}</td>
                    </tr>
                  </tbody>
                </table>
                </div>
                <p className="fund-src" style={{ marginTop: 6 }}>{t('fund.aumNote')}</p>
              </section>

              <section style={{ marginTop: 22 }}>
                <div className="sec-label">{t('fund.holdingsTitle')}
                  {holdings[0]?.as_of ? ` · ${t('fund.snapshot')} ${fmtDate(holdings[0].as_of)}` : ''}</div>
                {holdings.length ? (
                  <table>
                    <thead><tr><th>{t('fund.stock')}</th><th className="num">{t('fund.share')}</th></tr></thead>
                    <tbody>
                      {holdings.map((h) => (
                        <tr key={h.ticker}>
                          <td><Link to={lang === 'en'
                            ? `/en/stock/${h.ticker.toLowerCase()}`
                            : `/dionica/${h.ticker.toLowerCase()}`}><b>{h.ticker}</b></Link>{' '}
                            <span className="basis">{h.company_name}</span></td>
                          <td className="num">{num(h.pct, 2)} %</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <div className="subnote">{t('fund.noHoldings')}</div>}
                <p className="fund-src" style={{ marginTop: 6 }}>{t('fund.holdingsNote')}</p>
              </section>

              <div className="disc" style={{ marginTop: 24 }}>{t('fund.disc')}</div>
            </>
          )}
      </main>
      <SiteFooter />
    </div>
  )
}

/* Sekcija za stranicu dionice: OMF-ovi među top 10 te firme. */
export function OmfHolders({ ticker }) {
  const d = useFondovi()
  const { lang, t } = useLang()
  const rows = (d?.synergy || []).filter((s) => s.ticker === ticker)
  if (!rows.length) return null
  return (
    <section>
      <div className="sec-label">{t('fund.holdersTitle')}
        {rows[0]?.as_of ? ` · ${t('fund.snapshot')} ${fmtDate(rows[0].as_of)}` : ''}</div>
      <table>
        <thead><tr><th>{t('fund.fund')}</th><th className="num">{t('fund.share')}</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.holder_name}>
              <td>{r.fund} OMF — {t('fund.catLabel')} {r.category}
                <div className="fund-src">{r.holder_name}</div></td>
              <td className="num">{num(r.pct, 2)} %</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="fund-src">{t('fund.holdersSrc')}{' '}
        <Link to={lang === 'en' ? '/en/pension-funds' : '/mirovinski-fondovi'}>{t('fund.fundsPage')}</Link>.</p>
    </section>
  )
}
