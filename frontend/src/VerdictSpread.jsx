import React from 'react'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'
import { num } from './format.js'

const CLASS_COLORS = ['#9E2B25', '#2F5D86', '#6B4E8E', '#8A6D1F']

/**
 * Verdict spread: metode kao horizontalni rasponi (low–high, točka = base),
 * okomite linije = zadnje cijene klasa, zelena traka = zona min–max baza.
 * Redovi dolaze ISKLJUČIVO iz podataka (CROS: bez SOTP reda jer nije pokrenut).
 */
export default function VerdictSpread({ methods, classes, reconciliation, liquidity }) {
  const { lang, t } = useLang()
  const rows = methods.filter((m) => !m.no_value)
  const liqBy = {}
  ;(liquidity?.classes || []).forEach((l) => { liqBy[l.class_ticker] = l.flag })
  const prices = classes
    .filter((c) => c.last_price)
    .map((c, i) => ({
      ticker: c.ticker,
      price: c.last_price.close_eur,
      color: CLASS_COLORS[i % CLASS_COLORS.length],
      illiquid: liqBy[c.ticker] === 'low' || liqBy[c.ticker] === 'very_low',
    }))
  if (!rows.length) {
    return <p className="spread-note">{t('vs.noMethods')}</p>
  }

  const vals = [
    ...rows.flatMap((m) => [m.low, m.base, m.high]),
    ...prices.map((p) => p.price),
  ].filter((v) => v !== null && v !== undefined)
  const span = Math.max(...vals) - Math.min(...vals)
  const pad = span * 0.08 || 10
  const dmin = Math.min(...vals) - pad
  const dmax = Math.max(...vals) + pad

  const X0 = 150; const X1 = 940
  const rowH = 46; const topPad = 52
  const axisY = topPad + rows.length * rowH
  const H = axisY + 54
  const x = (v) => X0 + ((Math.min(dmax, Math.max(dmin, v)) - dmin) / (dmax - dmin)) * (X1 - X0)

  // os: ~6 zaobljenih koraka
  const rawStep = (dmax - dmin) / 5
  const mag = 10 ** Math.floor(Math.log10(rawStep))
  const step = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((s) => s >= rawStep) || rawStep
  const ticks = []
  for (let t = Math.ceil(dmin / step) * step; t <= dmax; t += step) ticks.push(t)

  const bases = rows.map((m) => m.base)
  const zLo = reconciliation ? reconciliation.zone_low : Math.min(...bases)
  const zHi = reconciliation ? reconciliation.zone_high : Math.max(...bases)

  return (
    <>
      <svg className="spread" viewBox={`0 0 1000 ${H}`} role="img" aria-label={t('vs.aria')}>
        <rect x={x(zLo)} y={topPad - 14} width={Math.max(2, x(zHi) - x(zLo))} height={axisY - topPad + 6}
          fill="#1F6E5A" opacity="0.08" />
        <line x1={X0} y1={axisY} x2={X1 + 30} y2={axisY} stroke="#C9CBC2" />
        <g fontFamily="IBM Plex Mono" fontSize="11" fill="#5C6772" textAnchor="middle">
          {ticks.map((t) => (
            <text key={t} x={x(t)} y={axisY + 18}>{num(t, step < 1 ? 1 : 0)}</text>
          ))}
          <text x={X1 + 30} y={axisY + 18} textAnchor="end">€</text>
        </g>
        {prices.map((p, i) => {
          // razmakni oznake kad su cijene klasa blizu (npr. CROS 3460 / CROS2 3360)
          const near = prices.some((q, j) => j !== i && Math.abs(x(q.price) - x(p.price)) < 90)
          const ly = near && i % 2 === 1 ? topPad - 40 : topPad - 26
          return (
            <g key={p.ticker}>
              <line x1={x(p.price)} y1={ly + 6} x2={x(p.price)} y2={axisY} stroke={p.color}
                strokeWidth="2" strokeDasharray={p.illiquid ? '4 4' : undefined} />
              <text x={x(p.price)} y={ly} textAnchor="middle" fontFamily="IBM Plex Mono"
                fontSize="11" fontWeight="600" fill={p.color}>
                {p.ticker} {num(p.price, 0)}{p.illiquid ? ' ⚠' : ''}
              </text>
            </g>
          )
        })}
        {rows.map((m, i) => {
          const y = topPad + i * rowH
          const role = reconciliation?.method_roles?.[m.key]?.role
          const isAnchor = role === 'anchor'
          // M8: sekundarne leće (i sidro isključeno iz zone) su PRIGUŠENE —
          // ostaju vidljive, ali ne vode; razlog odstupanja je u naraciji
          const op = role && !isAnchor ? 0.45 : 1
          const dotFill = isAnchor ? '#1F6E5A' : '#2E3B49'
          return (
            <g key={m.key} opacity={op}>
              <text x="8" y={y + 4} fontFamily="IBM Plex Sans" fontSize="13" fill="#1B242E">
                {tx(m.label, lang)}{role && !isAnchor ? ' *' : ''}
              </text>
              <line x1={x(m.low)} y1={y} x2={x(m.high)} y2={y} stroke="#9AA4AF" strokeWidth="7" strokeLinecap="round" />
              <circle cx={x(m.base)} cy={y} r="6" fill={dotFill} />
              <text x={x(m.high) + 10} y={y + 4} fontFamily="IBM Plex Mono" fontSize="13"
                fontWeight="700" fill="#1B242E">{num(m.base, 0)}</text>
            </g>
          )
        })}
      </svg>

      {reconciliation && (
        <div className="zoneout">
          <div>
            <div className="big">{num(reconciliation.zone_low, 0)}–{num(reconciliation.zone_high, 0)} €</div>
            <div className="lab">
              {reconciliation.anchor_methods?.length
                ? t('vs.zoneAnchored')
                : t('vs.zoneOverlap')}
            </div>
          </div>
          <div>
            <div className="big">{num(reconciliation.dispersion * 100, 0)}%</div>
            <div className="lab">
              {t('vs.dispersion')} {reconciliation.divergent ? t('vs.divergent') : t('vs.aligned')}
              {reconciliation.method_roles ? t('vs.secondaryNote') : ''}
            </div>
          </div>
        </div>
      )}
      <div className="legend">
        <span><i className="swatch" style={{ background: '#9AA4AF' }} /> {t('vs.range')}</span>
        <span><i className="dot" style={{ background: '#2E3B49' }} /> {t('vs.base')}</span>
        <span><i className="swatch" style={{ background: '#1F6E5A', opacity: 0.5 }} /> {t('vs.zone')}</span>
        {prices.map((p) => (
          <span key={p.ticker}>
            <i className="swatch" style={{ background: p.color }} /> {p.ticker} {t('vs.price')}
            {p.illiquid ? t('vs.illiq') : ''}
          </span>
        ))}
      </div>
    </>
  )
}
