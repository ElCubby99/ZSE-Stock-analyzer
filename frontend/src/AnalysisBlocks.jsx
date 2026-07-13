import React from 'react'
import { dash, eur, num } from './format.js'
import { Term } from './Legend.jsx'

/* QA flag (tehnički) -> jedna rečenica običnim jezikom; tehnički original
   ostaje dostupan iza klika (dvorazinski princip, ne mijenja izračun). */
export function plainFlag(f) {
  if (f.startsWith('ULAZI NEKONZISTENTNI')) {
    return ('Neke metode se ne slažu s glavnom procjenom — najčešće zato što dijelu '
      + 'podataka još fali kalibracija (npr. multiplikatori usporedivih firmi). '
      + 'Razliku bilježimo, ne skrivamo je.')
  }
  if (f.startsWith('metode se međusobno razilaze')) {
    return ('Različite metode daju vrlo različite brojke — to je signal za provjeru '
      + 'ulaznih podataka, ne za izbor najljepše brojke.')
  }
  if (f.startsWith('fer-zona odstupa')) {
    return ('Naša procjena je daleko od tržišne cijene — to je pitanje za provjeru '
      + 'pretpostavki, ne zaključak da je tržište u krivu.')
  }
  return f
}

/* DIO 1 — blokovi zone "02 · Analiza vrijednosti" po dizajnu:
   SIDRO panel (fer-zona + pozicije klasa + dvije SOTP brojke za holdinge),
   sekundarne metode s razlogom, rizici i kontekst (činjenice iz exporta),
   graf financija (prihod barovi + EBITDA linija) uz postojeću tablicu. */

const PINE = '#1F6E5A'
const OX = '#9E2B25'
const STEEL = '#2F5D86'

const METHOD_SHORT = {
  sotp_nav: 'SOTP / NAV', residual_income: 'REZIDUALNI DOHODAK',
  justified_pb_roe: 'OPRAVDANI P/B', dcf_fcf: 'DCF',
  multiples_relative: 'RELATIVNI MULTIPLI', ev_ebitda: 'EV/EBITDA',
  ddm_gordon: 'DIVIDENDNI DISKONT',
}

/* metoda -> pojam iz legende (tooltip na nazivu metode) */
const METHOD_TERM = {
  sotp_nav: 'SOTP', dcf_fcf: 'DCF', ev_ebitda: 'EV/EBITDA',
  ddm_gordon: 'DDM', justified_pb_roe: 'P/B',
}

export function AnchorPanel({ data }) {
  const rec = data.valuation?.reconciliation
  if (!rec || rec.zone_low === null) return null
  const sum = data.price_summary?.classes || []
  const classes = (data.share_classes || [])
    .map((c) => ({
      t: c.ticker,
      lbl: c.class_type === 'ordinary' ? 'redovna' : 'povlaštena',
      pref: c.class_type !== 'ordinary',
      p: sum.find((s) => s.class_ticker === c.ticker)?.last?.close_eur ?? null,
    }))
    .filter((c) => c.p !== null)
  const lo = rec.zone_low; const hi = rec.zone_high
  const d0m = Math.min(lo, ...classes.map((c) => c.p))
  const d1m = Math.max(hi, ...classes.map((c) => c.p))
  const pad = (d1m - d0m) * 0.14 || d1m * 0.05
  const d0 = d0m - pad; const d1 = d1m + pad
  const P = (v) => Math.max(1.5, Math.min(98.5, ((v - d0) / (d1 - d0)) * 100))
  const pos = (p) => (p > hi ? `${num((p / hi - 1) * 100, 1)}% iznad zone`
    : p < lo ? `${num((1 - p / lo) * 100, 1)}% ispod zone` : 'unutar zone')
  const sotp = data.valuation?.sotp
  // M12: primarno sidro nosi zonu; ostala sidra istog arhetipa su potvrda
  const roles = rec.method_roles || {}
  const prim = Object.keys(roles).find((k) => roles[k].role === 'anchor')
  const alts = Object.keys(roles).filter((k) => roles[k].role === 'anchor_alt')
  const anchorName = prim
    ? (METHOD_SHORT[prim] || prim)
    : (rec.anchor_methods || []).map((k) => METHOD_SHORT[k] || k).join(' + ')

  return (
    <div className="anch">
      <div className="anch-head">
        <span className="anch-tag"><Term t="sidro">SIDRO</Term> · {anchorName || dash}</span>
        <span className="anch-sub">
          {alts.length
            ? `zona = sidro ± osjetljivost; potvrda: ${alts.map((k) => METHOD_SHORT[k] || k).join(', ')}`
            : 'glavna fer-zona — sve metode se mjere prema njoj'}
        </span>
      </div>
      <div className="anch-zone">{num(lo, 2)}–{num(hi, 2)} €</div>
      <p className="anch-plain">
        <Term t="fer-zona">Fer-zona</Term> je naša procjena vrijednosti dionice.
        Cijena iznad zone znači da tržište plaća više nego što fundamenti govore;
        ispod zone — obrnuto. Zaključak je vaš.
      </p>
      <div className="anch-band">
        <div className="anch-axis" />
        <div className="anch-fill" style={{ left: `${P(lo)}%`, width: `${P(hi) - P(lo)}%` }} />
        <div className="anch-lbl" style={{ left: `${P(lo)}%` }}>{num(lo, 0)}</div>
        <div className="anch-lbl" style={{ left: `${P(hi)}%` }}>{num(hi, 0)}</div>
        {classes.map((c) => (
          <React.Fragment key={c.t}>
            <div className="anch-tick-lbl" style={{ left: `${P(c.p)}%` }}>
              <b style={{ color: c.pref ? STEEL : OX }}>{c.t}</b> {num(c.p, 2)} €
            </div>
            <div className="anch-tick" style={{ left: `${P(c.p)}%`, background: c.pref ? STEEL : OX }} />
          </React.Fragment>
        ))}
      </div>
      <div className="anch-foot">
        {classes.map((c) => (
          <span key={c.t}>
            <i style={{ background: c.pref ? STEEL : OX }} />
            <b>{c.t}</b> <em>{c.lbl}</em> {num(c.p, 2)} € — {pos(c.p)}
          </span>
        ))}
      </div>
      {rec.reasoning && (
        <div className="anch-chain">
          <div className="prof-klabel">KAKO SMO DOŠLI DO SIDRA</div>
          <p>{rec.reasoning}</p>
          {rec.zone_note && <div className="anch-chain-note">{rec.zone_note}</div>}
        </div>
      )}
      {(rec.qa_flags || []).length > 0 && (
        <div className="anch-qa">
          {rec.qa_flags.map((f, i) => (
            <div className="anch-qa-row" key={i}>
              <span className="flag">QA</span> {plainFlag(f)}
              {plainFlag(f) !== f && (
                <details className="anch-qa-tech">
                  <summary>tehnički zapis</summary>
                  {f}
                </details>
              )}
            </div>
          ))}
        </div>
      )}
      {sotp && sotp.sotp_fair && sotp.sotp_market && (
        <div className="anch-sotp2">
          <div>
            <div className="prof-klabel">SOTP PO NAŠOJ PROCJENI</div>
            <div className="anch-sotp2-v" style={{ color: PINE }}>
              {num(sotp.sotp_fair.base_per_share, 2)} €
            </div>
            <div className="anch-sotp2-n">{sotp.sotp_fair.note} · sidro fer-zone</div>
          </div>
          <div>
            <div className="prof-klabel">SOTP PO TRŽIŠTU</div>
            <div className="anch-sotp2-v">{num(sotp.sotp_market.base_per_share, 2)} €</div>
            <div className="anch-sotp2-n">{sotp.sotp_market.note}</div>
          </div>
          {sotp.market_vs_fair_pct !== null && sotp.market_vs_fair_pct !== undefined && (
            <div>
              <div className="prof-klabel">SIGNAL RAZLIKE</div>
              <div className="anch-sotp2-v" style={{
                color: sotp.market_vs_fair_pct > 0 ? OX : PINE }}>
                {sotp.market_vs_fair_pct > 0 ? '+' : ''}{num(sotp.market_vs_fair_pct, 1)}%
              </div>
              <div className="anch-sotp2-n">
                tržište vrednuje uvrštene kćeri {sotp.market_vs_fair_pct > 0 ? 'iznad' : 'ispod'} naše
                procjene — činjenica, ne preporuka
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function SecondaryList({ data }) {
  const rec = data.valuation?.reconciliation
  if (!rec?.method_roles) return null
  const ran = (data.valuation.ran || []).filter((m) => !m.no_value)
  const secs = ran.filter((m) => {
    const r = rec.method_roles[m.key]
    return r && r.role !== 'anchor'
  })
  if (!secs.length) return null
  return (
    <div className="sec-list">
      <div className="sec-list-h">SEKUNDARNE METODE — ZAŠTO ODSTUPAJU OD SIDRA</div>
      {secs.map((m) => {
        const r = rec.method_roles[m.key]
        const dev = r.vs_zone_pct
        return (
          <div className="sec-list-row" key={m.key}>
            <span className="sec-list-name">
              {METHOD_TERM[m.key]
                ? <Term t={METHOD_TERM[m.key]}>{METHOD_SHORT[m.key] || m.label}</Term>
                : (METHOD_SHORT[m.key] || m.label)}
            </span>
            <span className="sec-list-val">
              {num(m.base, 2)} €{dev ? ` (${dev > 0 ? '+' : ''}${num(dev * 100, 0)}%)` : ''}
            </span>
            <span className="sec-list-note">
              {r.role === 'anchor_excluded' ? r.note : r.note}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export function Risks({ risks }) {
  if (!risks || !risks.cards.length) return null
  return (
    <>
      <h3 className="prof-h3" style={{ marginBottom: 4 }}>Rizici i kontekst</h3>
      <p className="risk-sub">{risks.note}</p>
      <div className="risk-grid">
        {risks.cards.map((c) => (
          <div className="risk-card" key={c.l}>
            <div className="risk-l">{c.l}</div>
            <div className="risk-t">{c.txt}</div>
          </div>
        ))}
      </div>
    </>
  )
}

/* graf financija po dizajnu: prihod = obrisi barova (steel), EBITDA = linija (borova) */
export function FinChart({ trend }) {
  if (!trend || !trend.series.length) return null
  const s = trend.series
  const vals = s.flatMap((r) => [r.revenue, r.ebitda]).filter((v) => v !== null)
  if (!vals.length) return null
  const vmax = Math.max(...vals)
  const W = 560; const H = 200; const base = 174; const top = 30
  const gw = (W - 40) / s.length
  const yH = (v) => ((v / vmax) * (base - top))
  const bx = (i) => 20 + i * gw + gw / 2 - 40
  const ebPts = s.filter((r) => r.ebitda !== null)
  return (
    <div className="prof-panel" style={{ marginBottom: 0 }}>
      <div className="prof-panel-head">
        <span className="prof-klabel">{trend.revenue_label.toUpperCase()} I EBITDA · MLN €</span>
        <span className="prof-legend" style={{ fontSize: 10 }}>
          <i style={{ display: 'inline-block', width: 12, height: 8,
            background: 'rgba(47,93,134,0.28)', border: `1px solid ${STEEL}` }} /> {trend.revenue_label.toLowerCase()}
          <i style={{ display: 'inline-block', width: 14, height: 2, background: PINE, marginLeft: 8 }} /> <Term t="EBITDA">EBITDA</Term>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
        <line x1="20" x2={W - 20} y1={base} y2={base} stroke="rgba(38,46,51,0.25)" />
        {s.map((r, i) => r.revenue !== null && (
          <g key={r.year}>
            <rect x={bx(i)} y={base - yH(r.revenue)} width="80" height={yH(r.revenue)}
              fill="rgba(47,93,134,0.28)" stroke={STEEL} />
            <text x={bx(i) + 40} y={base - yH(r.revenue) - 6} textAnchor="middle"
              fontFamily="IBM Plex Mono" fontSize="11" fill={STEEL}>{num(r.revenue / 1e6, 0)}</text>
            <text x={bx(i) + 40} y={base + 16} textAnchor="middle"
              fontFamily="IBM Plex Mono" fontSize="11" fill="rgba(38,46,51,0.55)">FY{r.year}</text>
          </g>
        ))}
        {ebPts.length >= 2 && (
          <polyline fill="none" stroke={PINE} strokeWidth="1.8"
            points={s.map((r, i) => r.ebitda !== null
              ? `${bx(i) + 40},${base - yH(r.ebitda)}` : null).filter(Boolean).join(' ')} />
        )}
        {s.map((r, i) => r.ebitda !== null && (
          <g key={`e${r.year}`}>
            <circle cx={bx(i) + 40} cy={base - yH(r.ebitda)} r="3" fill={PINE} />
            <text x={bx(i) + 40} y={base - yH(r.ebitda) - 8} textAnchor="middle"
              fontFamily="IBM Plex Mono" fontSize="10.5" fill={PINE}>{num(r.ebitda / 1e6, 0)}</text>
          </g>
        ))}
      </svg>
      <div className="prof-panel-note" style={{ borderTop: '1px solid rgba(38,46,51,0.15)', paddingTop: 10 }}>
        {trend.narration}
      </div>
    </div>
  )
}
