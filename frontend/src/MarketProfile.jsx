import React, { useMemo, useState } from 'react'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'
import { dash, eur, fmtDate, num, pct } from './format.js'

/* Tržišni profil (GORE) — dizajnerski jezik "Burzovni list": IBM Plex,
   papir #F2F3EF / paneli #F7F8F4, oksblood #9E2B25 (tržišna cijena),
   steel #2F5D86 (povlaštene, izglasane isplate), borova #1F6E5A (fer-zona).
   Sve brojke dolaze iz exporta (price_summary / prices / dividend_calendar /
   metrics / valuation.reconciliation) — ništa se ne računa izvan baze.
   M38: UI tekstovi kroz t(), podatkovni tekstovi kroz tx(). */

const INK = '#262E33'
const OX = '#9E2B25'
const STEEL = '#2F5D86'
const PINE = '#1F6E5A'

export function SectionRule({ n, title }) {
  return (
    <div className="prof-rule">
      <span className="prof-rule-n">{n}</span>
      <h2>{title}</h2>
      <div className="prof-rule-line" />
    </div>
  )
}

/* mini fer-zona traka u headeru: pojas zone + okomita crta cijene */
function GapBand({ zone, price, pref }) {
  const { t } = useLang()
  if (!zone || price === null || price === undefined) return null
  const [lo, hi] = zone
  const d0m = Math.min(lo, price); const d1m = Math.max(hi, price)
  const pad = (d1m - d0m) * 0.22 || d1m * 0.06
  const d0 = d0m - pad; const d1 = d1m + pad
  const p = (v) => Math.max(1.5, Math.min(98.5, ((v - d0) / (d1 - d0)) * 100))
  let gap = 0
  if (price > hi) gap = (price / hi - 1) * 100
  else if (price < lo) gap = -(1 - price / lo) * 100
  const gapLabel = gap === 0 ? t('idx.inside')
    : gap > 0 ? `+${num(gap, 1)} ${t('mp.pctAbove')}` : `−${num(Math.abs(gap), 1)} ${t('mp.pctBelow')}`
  return (
    <div>
      <div className="prof-klabel">{t('mp.gapVsZone')}</div>
      <div className="prof-band">
        <div className="prof-band-axis" />
        <div className="prof-band-zone" style={{ left: `${p(lo)}%`, width: `${p(hi) - p(lo)}%` }} />
        <div className="prof-band-tick" style={{ left: `${p(price)}%`, background: pref ? STEEL : OX }} />
      </div>
      <div className="prof-band-sub">{t('stock.fairZone')} {num(lo, 0)}–{num(hi, 0)} € · {gapLabel}</div>
    </div>
  )
}

export function ProfileHeader({ data, zone }) {
  const { t } = useLang()
  const sum = data.price_summary?.classes || []
  const primary = data.share_classes.find((c) => c.is_primary) || data.share_classes[0]
  return (
    <div className="prof-head">
      <div>
        <div className="prof-title">
          <h1>{data.name} ({data.ticker}) — {t('stock.analysisTitle')}</h1>
          <span className="prof-tk">{data.ticker}</span>
        </div>
        <div className="prof-subline">
          {data.sector_hr || data.sector || t('stock.unknownSector')} · {t('stock.zseEur')}
        </div>
      </div>
      <div className="prof-head-right">
        {sum.map((s) => {
          const cls = data.share_classes.find((c) => c.ticker === s.class_ticker)
          const pref = cls && cls.class_type !== 'ordinary'
          return (
            <div key={s.class_ticker}>
              <div className="prof-klabel">
                {t('mp.marketPrice')}{sum.length > 1 ? ` · ${s.class_ticker}` : ''}
              </div>
              {s.last ? (
                <div className="prof-price-row">
                  <span className="prof-price" style={{ color: pref ? STEEL : OX }}>
                    {num(s.last.close_eur, 2)} €
                  </span>
                  <span className="prof-chg" style={{
                    color: s.change_pct > 0 ? PINE : s.change_pct < 0 ? OX : 'rgba(38,46,51,0.55)',
                  }}>
                    {s.change_pct === null || s.change_pct === undefined ? dash
                      : `${s.change_pct > 0 ? '+' : s.change_pct < 0 ? '−' : '±'}${num(Math.abs(s.change_pct) * 100, 2)} %`}
                  </span>
                </div>
              ) : <div className="prof-price-row"><span className="prof-price">{dash}</span></div>}
              {s.last && <div className="prof-band-sub">{s.last.date}</div>}
            </div>
          )
        })}
        {zone && primary && (
          <GapBand
            zone={zone}
            price={sum.find((s) => s.class_ticker === primary.ticker)?.last?.close_eur ?? null}
            pref={false}
          />
        )}
      </div>
    </div>
  )
}

export function IlliquidBanner({ liquidity }) {
  const { lang, t } = useLang()
  const flagged = (liquidity?.classes || []).filter((c) => c.flag !== 'ok')
  if (!flagged.length) return null
  const veryLow = flagged.some((c) => c.flag === 'very_low')
  return (
    <div className="prof-illiq">
      <span className="prof-illiq-t">{veryLow ? t('mp.veryPrefix') : ''}{t('mp.illiquidStock')}</span>
      <span className="prof-illiq-n">
        {flagged.map((c) => `${c.class_ticker}: ${tx(c.note, lang)}`).join(' · ')}{t('mp.illiqNote')}
      </span>
    </div>
  )
}

/* ---------- graf cijene ---------- */

const RANGES = [
  { key: '1M', days: 31, lbl: 'mp.r1m' },
  { key: '6M', days: 183, lbl: 'mp.r6m' },
  { key: '1G', days: 366, lbl: 'mp.r1g' },
  { key: '5G', days: 1830, lbl: 'mp.r5g' },
]

export function PriceChart({ data, zone, classZones }) {
  const { t } = useLang()
  const classes = data.share_classes
  const [clsTk, setClsTk] = useState(
    (classes.find((c) => c.is_primary) || classes[0] || {}).ticker)
  const [range, setRange] = useState('1G')
  /* v3 S: zona PO KLASI (ista vrijednost firme, tržišni omjer klasa) */
  const cz = classZones && classZones[clsTk]
  const zoneEff = cz ? [cz.zone_low, cz.zone_high] : zone

  const series = useMemo(() => (data.prices || [])
    .filter((p) => p.class_ticker === clsTk && p.close_eur !== null)
    .sort((a, b) => (a.trade_date < b.trade_date ? -1 : 1)), [data.prices, clsTk])

  if (!series.length) {
    return (
      <div className="prof-panel">
        <div className="prof-panel-head"><span className="prof-klabel">{t('mp.price')} · {data.ticker} · EUR</span></div>
        <div className="prof-empty">{t('mp.noPrices')}</div>
      </div>
    )
  }

  const lastDate = series[series.length - 1].trade_date
  const rc = RANGES.find((r) => r.key === range) || RANGES[2]
  const cut = new Date(lastDate)
  cut.setDate(cut.getDate() - rc.days)
  const cutIso = cut.toISOString().slice(0, 10)
  const pts = series.filter((p) => p.trade_date >= cutIso)
  const clipped = pts.length ? pts : series
  // 5G (i svaki raspon dublji od povijesti): crtamo SAMO do dostupne dubine
  const truncated = rc.days > 400 && series[0].trade_date > cutIso

  const W = 760; const H = 230; const pT = 12; const pB = 26; const pL = 10; const pR = 66
  const vals = clipped.map((p) => p.close_eur)
  let vMin = Math.min(...vals); let vMax = Math.max(...vals)
  if (zoneEff) { vMin = Math.min(vMin, zoneEff[0]); vMax = Math.max(vMax, zoneEff[1]) }
  const vPad = (vMax - vMin) * 0.07 || vMax * 0.03
  vMin -= vPad; vMax += vPad
  const n = clipped.length - 1 || 1
  const yF = (v) => pT + ((vMax - v) / (vMax - vMin)) * (H - pT - pB)
  const xF = (i) => pL + (i / n) * (W - pL - pR)
  const poly = clipped.map((p, i) => `${xF(i).toFixed(1)},${yF(p.close_eur).toFixed(1)}`).join(' ')
  const last = clipped[clipped.length - 1]
  const gy = [0.25, 0.5, 0.75].map((f) => (pT + (H - pT - pB) * f).toFixed(1))
  const x2 = W - pR

  const cls = classes.find((c) => c.ticker === clsTk)
  const pref = cls && cls.class_type !== 'ordinary'
  const lineCol = pref ? STEEL : OX

  return (
    <div className="prof-panel">
      <div className="prof-panel-head">
        <span className="prof-klabel">{t('mp.price')} · {clsTk} · EUR</span>
        <div className="prof-chips">
          {classes.length > 1 && classes.map((c) => (
            <button key={c.ticker} className={`prof-chip ${clsTk === c.ticker ? 'on' : ''}`}
              onClick={() => setClsTk(c.ticker)}>{c.ticker}</button>
          ))}
          {classes.length > 1 && <span className="prof-chip-gap" />}
          {RANGES.map((r) => (
            <button key={r.key} className={`prof-chip ${range === r.key ? 'on' : ''}`}
              onClick={() => setRange(r.key)}>{t(r.lbl)}</button>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}
        role="img" aria-label={`${t('mp.priceAria')} ${clsTk}`}>
        {gy.map((y) => <line key={y} x1={pL} x2={x2} y1={y} y2={y} stroke="rgba(38,46,51,0.09)" />)}
        {zoneEff && (
          <>
            <rect x={pL} y={yF(zoneEff[1])} width={x2 - pL} height={Math.max(0, yF(zoneEff[0]) - yF(zoneEff[1]))}
              fill="rgba(31,110,90,0.10)" />
            <line x1={pL} x2={x2} y1={yF(zoneEff[1])} y2={yF(zoneEff[1])} stroke={PINE} strokeDasharray="3 4" opacity="0.7" />
            <line x1={pL} x2={x2} y1={yF(zoneEff[0])} y2={yF(zoneEff[0])} stroke={PINE} strokeDasharray="3 4" opacity="0.7" />
            <text x={x2 + 8} y={(yF(zoneEff[0]) + yF(zoneEff[1])) / 2 + 3.5} fill={PINE}
              fontFamily="IBM Plex Mono" fontSize="10">{t('stock.fairZone')}</text>
          </>
        )}
        <polyline points={poly} fill="none" stroke={lineCol} strokeWidth="1.6"
          strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={xF(clipped.length - 1)} cy={yF(last.close_eur)} r="3.5" fill={lineCol} />
        <text x={x2 + 8} y={yF(last.close_eur)} dy="4" fill={lineCol}
          fontFamily="IBM Plex Mono" fontSize="11" fontWeight="600">{num(last.close_eur, 2)}</text>
        <text x={pL + 4} y="20" fill="rgba(38,46,51,0.45)" fontFamily="IBM Plex Mono" fontSize="10">{num(vMax, 2)}</text>
        <text x={pL + 4} y={H - 12} fill="rgba(38,46,51,0.45)" fontFamily="IBM Plex Mono" fontSize="10">{num(vMin, 2)}</text>
      </svg>
      <div className="prof-panel-foot">
        <span>{fmtDate(clipped[0].trade_date)}{truncated ? t('mp.histStart') : ''}</span>
        <span className="prof-legend">
          <i className="prof-sw" style={{ background: lineCol }} /> {t('mp.marketPriceEod')}
          {zoneEff && <><i className="prof-sw-zone" /> {t('mkt.legendZone')}</>}
        </span>
        <span>{fmtDate(last.trade_date)}</span>
      </div>
      <div className="prof-panel-note">
        {t('mp.tradedDays1')} ({clipped.length} {t('mp.tradedDays2')})
      </div>
    </div>
  )
}

/* ---------- ključni podaci ---------- */

export function StatsStrip({ data }) {
  const { lang, t } = useLang()
  const primary = data.share_classes.find((c) => c.is_primary) || data.share_classes[0] || {}
  const sum = (data.price_summary?.classes || []).find((s) => s.class_ticker === primary.ticker)
  const perCls = (data.metrics?.per_class || []).find((r) => r.class_ticker === primary.ticker)
  const m = data.metrics || {}
  const tiles = [
    {
      l: t('mp.stat52w'),
      v: sum && sum.high_52w_eur !== null && sum.high_52w_eur !== undefined
        ? `${num(sum.low_52w_eur, 2)}–${num(sum.high_52w_eur, 2)} €` : dash,
      n: sum?.note ? tx(sum.note, lang) : null,
    },
    {
      l: t('mp.statMcap'),
      v: m.market_cap_eur ? `${num(m.market_cap_eur / 1e6, 0)} ${t('mp.milEur')}` : t('mkt.indicesNone'),
    },
    {
      l: t('mp.statTurnover'),
      v: sum && sum.avg_turnover_20d_eur ? eur(sum.avg_turnover_20d_eur, 0) : dash,
      n: t('mp.turnoverBasis'),
    },
    { l: 'P/E', v: perCls && perCls.pe !== null ? num(perCls.pe, 1) : t('mkt.indicesNone') },
    { l: 'P/B', v: perCls && perCls.pb !== null ? num(perCls.pb, 2) : t('mkt.indicesNone') },
    {
      l: t('mp.statDivYield'),
      v: perCls && perCls.div_yield ? pct(perCls.div_yield, 2) : dash,
      n: m.dps ? `DPS ${eur(m.dps)}` : null,
    },
  ]
  return (
    <div className="prof-stats">
      {tiles.map((t_) => (
        <div className="prof-stat" key={t_.l}>
          <div className="prof-klabel">{t_.l}</div>
          <div className="prof-stat-v">{t_.v}</div>
          {t_.n && <div className="prof-stat-n">{t_.n}</div>}
        </div>
      ))}
    </div>
  )
}

/* ---------- dividende ---------- */

export function Dividends({ data }) {
  const { lang, t } = useLang()
  const cal = data.dividend_calendar
  if (!cal) return null
  const multi = data.share_classes.length > 1
  const paid = cal.events.filter((e) => e.status === 'paid')
  const pending = cal.events.filter((e) => e.status !== 'paid')
  // najbliža nadolazeća: izglasana ima prednost pred prijedlogom
  const next = pending.find((e) => e.status === 'upcoming') || pending[0] || null

  const h = cal.history
  return (
    <>
      <h3 className="prof-h3">{t('nav.dividends')}</h3>
      {h && (
        <div className="div-hist-strip">
          <span><b>{h.continuity.paid_years} {t('mp.of5')}</b> {t('mp.lastFyWithPayout')}
            {' '}<i className="fund-src">({t('mp.dataFromFy')}{h.continuity.coverage_from})</i></span>
          <span>{t('mp.avg5y')} <b>{num(h.avg_amount_5y, 2)} €</b>{t('mp.perShare')}</span>
          <span>{t('mp.divGrowth')} <b>{h.growth_cagr !== null && h.growth_cagr !== undefined
            ? `${h.growth_cagr > 0 ? '+' : ''}${num(h.growth_cagr * 100, 1)} ${t('mp.pctPerYear')}` : t('common.na')}</b>
            {' '}<i className="fund-src">({tx(h.growth_note, lang)})</i></span>
        </div>
      )}
      {cal.d_sust && cal.d_sust.d_sust_ps !== null && cal.d_sust.d_sust_ps !== undefined && (
        <div className="div-hist-strip">
          <span>{t('mp.dsustLabel')} <b>{num(cal.d_sust.d_sust_ps, 2)} €</b>{t('mp.perShare')}
            {cal.d_sust.flags && cal.d_sust.flags.length > 0 && (
              <> {cal.d_sust.flags.map((f) => <span key={f} className="flag"> {tx(f, lang)}</span>)}</>
            )}
          </span>
          <details className="src-details"><summary>{t('mp.fullBreakdown')}</summary>
            <div className="src">
              {cal.d_sust.fallback_raw
                ? tx(cal.d_sust.note, lang)
                : `${t('mp.ds1')} ${num((cal.d_sust.payout_used || 0) * 100, 0)} % (${tx(cal.d_sust.payout_basis, lang)}) ${t('mp.ds2')} ${cal.d_sust.excluded_years && cal.d_sust.excluded_years.length ? `${t('mp.dsExcluded')} ${cal.d_sust.excluded_years.join(', ')}. ` : ''}${cal.d_sust.coverage_announced ? `${t('mp.dsCoverage')} ${num(cal.d_sust.coverage_announced, 2)}×. ` : ''}${tx(cal.d_sust.note, lang)}`}
            </div>
          </details>
        </div>
      )}
      <div className="prof-div-grid">
        <div>
          {paid.length ? (
            <table className="prof-div-table">
              <thead>
                <tr>
                  <th>{t('mp.colFy')}</th>
                  {multi && <th>{t('mp.colClass')}</th>}
                  <th className="num">{t('mp.colAmount')}</th>
                  <th className="num">{t('div.col.payout')}</th>
                  <th>{t('mp.colType')}</th>
                  <th className="num">{t('div.col.ex')}</th>
                  <th className="num">{t('div.col.pay')}</th>
                </tr>
              </thead>
              <tbody>
                {paid.map((e, i) => (
                  <tr key={i}>
                    <td>{e.fiscal_year ? `${e.fiscal_year}.` : dash}</td>
                    {multi && <td>{e.class_ticker}</td>}
                    <td className="num strong">{num(e.amount_eur, 2)} €</td>
                    <td className="num">{e.payout_ratio === null || e.payout_ratio === undefined
                      ? <i className="np" title={`${t('mp.profitFy1')}${e.fiscal_year ?? '?'}${t('mp.profitFy2')}`}>—</i>
                      : e.payout_ratio > 1
                        ? <span title={tx(e.classified_reason, lang) || ''}>{t('div.payoutOver')}</span>
                        : <span title={tx(e.classified_reason, lang) || ''}>{num(e.payout_ratio * 100, 0)} %</span>}</td>
                    <td>{e.payout_type ? (e.payout_type === 'redovna'
                      ? <span className="div-onoff reg" title={tx(e.classified_reason, lang) || ''}>{t('div.type.regular')}</span>
                      : <span className="div-onoff" title={tx(e.classified_reason, lang) || ''}>
                        {e.payout_type === 'iz_zadrzane_dobiti' ? t('div.type.retained') : t('div.type.extraordinary')}</span>) : dash}</td>
                    <td className="num">{e.ex_date ? fmtDate(e.ex_date) : dash}</td>
                    <td className="num">{e.payment_date ? fmtDate(e.payment_date) : dash}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="prof-empty-box">
              {t('mp.noPaid')}
            </div>
          )}
          <div className="prof-panel-note">{tx(cal.note, lang)}</div>
          <div className="prof-panel-note">
            {t('mp.leg1')} <b>{t('div.type.regular')}</b> {t('mp.leg2')}{' '}
            <b>{t('div.type.extraordinary')}</b> {t('mp.leg3')}{' '}
            <b>{t('div.type.retained')}</b> {t('mp.leg4')}
          </div>
        </div>
        <div>
          {next ? next.status === 'upcoming' ? (
            <div className="prof-next prof-next-firm">
              <div className="prof-next-label" style={{ color: STEEL }}>
                {t('mp.approvedPayout')} · {next.fiscal_year ? `${t('mp.fromProfitOf')} ${next.fiscal_year}.` : ''}
                {multi ? ` · ${next.class_ticker}` : ''}
              </div>
              <div className="prof-next-amt">{num(next.amount_eur, 2)} €</div>
              <div className="prof-next-dates">
                <span><i>{t('div.col.ex')} </i>{next.ex_date ? fmtDate(next.ex_date) : dash}</span>
                <span><i>{t('div.col.pay')} </i>{next.payment_date ? fmtDate(next.payment_date) : dash}</span>
              </div>
              <div className="prof-next-src">
                {t('mp.perShareNote')}{' '}
                {next.source_url ? <a href={next.source_url} target="_blank" rel="noreferrer">{t('mp.companyFiling')}</a> : t('mp.companyFiling')}
              </div>
            </div>
          ) : (
            <div className="prof-next prof-next-prop">
              <div className="prof-next-label prof-warn-t">
                {t('mp.proposalTitle')}
                {multi ? ` · ${next.class_ticker}` : ''}
              </div>
              <div className="prof-next-amt">{num(next.amount_eur, 2)} €</div>
              <div className="prof-next-dates">
                <span><i>{t('div.col.ex')} </i>{next.ex_date ? fmtDate(next.ex_date) : dash}</span>
                <span><i>{t('div.col.pay')} </i>{next.payment_date ? fmtDate(next.payment_date) : dash}</span>
              </div>
              <div className="prof-next-src">
                {t('mp.proposalNote')}{' '}
                {next.source_url ? <a href={next.source_url} target="_blank" rel="noreferrer">{t('mp.companyFiling')}</a> : t('mp.companyFiling')}
              </div>
            </div>
          ) : (
            <div className="prof-empty-box">{t('mp.noUpcoming')}</div>
          )}
        </div>
      </div>
    </>
  )
}

/* ---------- prazno stanje analize (market_only) ---------- */

export function AnalysisUnavailable({ note }) {
  const { lang, t } = useLang()
  return (
    <div className="prof-unavail">
      <div className="prof-klabel">{t('mp.analysisNa')}</div>
      <p>{tx(note, lang)}</p>
      <p className="prof-panel-note">
        {t('mp.analysisNa1')} <b>{t('mkt.indicesNone')}</b> {t('mp.analysisNa2')}
      </p>
    </div>
  )
}
