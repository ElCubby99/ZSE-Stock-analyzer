import React from 'react'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'
import { dash, num, zoneDec } from './format.js'
import { Term } from './Legend.jsx'

/* QA flag (tehnički) -> jedna rečenica običnim jezikom; tehnički original
   ostaje dostupan iza klika (dvorazinski princip, ne mijenja izračun).
   Prefiksi usporedbe su HR podatkovne konstante iz exporta — dijakritici
   idu unicode escapeom (i18n lint), a prijevod rečenica kroz t(). */
export function plainFlag(f, t) {
  if (f.startsWith('ULAZI NEKONZISTENTNI')) return t('ab.qa1')
  if (f.startsWith('metode se me\u0111usobno razilaze')) return t('ab.qa2')
  if (f.startsWith('fer-zona odstupa')) return t('ab.qa3')
  return f
}

/* DIO 1 — blokovi zone "02 · Analiza vrijednosti" po dizajnu:
   SIDRO panel (fer-zona + pozicije klasa + dvije SOTP brojke za holdinge),
   sekundarne metode s razlogom, rizici i kontekst (činjenice iz exporta),
   graf financija (prihod barovi + EBITDA linija) uz postojeću tablicu. */

const PINE = '#1F6E5A'
const OX = '#9E2B25'
const STEEL = '#2F5D86'

/* metoda -> i18n ključ kratkog naziva (t()) */
const METHOD_SHORT_KEY = {
  sotp_nav: 'ab.m.sotp_nav', nav_fund: 'ab.m.nav_fund', residual_income: 'ab.m.residual_income',
  justified_pb_roe: 'ab.m.justified_pb_roe', dcf_fcf: 'ab.m.dcf_fcf',
  comps: 'ab.m.comps',
  multiples_relative: 'ab.m.multiples_relative', ev_ebitda: 'ab.m.ev_ebitda',
  ddm_gordon: 'ab.m.ddm_gordon', pro_forma_ev_ebitda: 'ab.m.pro_forma_ev_ebitda',
}
const methodShort = (key, t, fallback) =>
  (METHOD_SHORT_KEY[key] ? t(METHOD_SHORT_KEY[key]) : (fallback || key))

/* metoda -> pojam iz legende (tooltip na nazivu metode) */
const METHOD_TERM = {
  sotp_nav: 'SOTP', dcf_fcf: 'DCF', ev_ebitda: 'EV/EBITDA',
  ddm_gordon: 'DDM', justified_pb_roe: 'P/B',
}

export function AnchorPanel({ data }) {
  const { lang, t } = useLang()
  const rec = data.valuation?.reconciliation
  // M51: nema fer-zone -> objasni ZAŠTO (činjenice iz izvješća), ne prazno
  const nvd = data.valuation?.no_value_data
  if ((!rec || rec.zone_low === null) && nvd) {
    return (
      <div className="anch anch-held">
        <div className="anch-head">
          <span className="anch-tag" style={{ color: OX }}>{t('ab.noValueTag')}</span>
        </div>
        <p className="anch-plain">
          {t('ab.noValueIntro')}
          {nvd.negative_equity_eur !== undefined && (
            <> {t('ab.noValueNegEq')} <b>{num(nvd.negative_equity_eur / 1e6, 1)} {t('ab.mEur')}</b>.</>
          )}
          {nvd.net_loss_eur !== undefined && (
            <> {t('ab.noValueLoss')} <b>{num(nvd.net_loss_eur / 1e6, 1)} {t('ab.mEur')}</b>.</>
          )}
          {' '}{t('ab.noValueOutro')}
        </p>
      </div>
    )
  }
  if (!rec || rec.zone_low === null) return null
  // v2 §8 RED RULES: analiza ne ide live dok se pravila ne razriješe
  if ((rec.red_rules || []).length > 0) {
    return (
      <div className="anch anch-held">
        <div className="anch-head">
          <span className="anch-tag" style={{ color: OX }}>{t('ab.held')}</span>
        </div>
        <p className="anch-plain">
          {t('ab.heldNote')}
        </p>
        <ul className="anch-red-list">
          {rec.red_rules.map((r, i) => <li key={i}>{tx(r, lang)}</li>)}
        </ul>
      </div>
    )
  }
  const sum = data.price_summary?.classes || []
  const classes = (data.share_classes || [])
    .map((c) => ({
      t: c.ticker,
      lbl: c.class_type === 'ordinary' ? t('ab.ordinary') : t('ab.preferred'),
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
  const pos = (p) => (p > hi ? `${num((p / hi - 1) * 100, 1)}${t('ab.pctAboveZone')}`
    : p < lo ? `${num((1 - p / lo) * 100, 1)}${t('ab.pctBelowZone')}` : t('ab.insideZone'))
  const sotp = data.valuation?.sotp
  // M12: primarno sidro nosi zonu; ostala sidra istog arhetipa su potvrda
  const roles = rec.method_roles || {}
  const prim = Object.keys(roles).find((k) => roles[k].role === 'anchor')
  const alts = Object.keys(roles).filter((k) => roles[k].role === 'anchor_alt')
  const anchorName = prim
    ? methodShort(prim, t)
    : (rec.anchor_methods || []).map((k) => methodShort(k, t)).join(' + ')

  return (
    <div className="anch">
      <div className="anch-head">
        <span className="anch-tag"><Term t="sidro">{t('ab.anchorTag')}</Term> · {anchorName || dash}</span>
        <span className="anch-sub">
          {alts.length
            ? `${t('ab.subConfirm')} ${alts.map((k) => methodShort(k, t)).join(', ')}`
            : t('ab.subMain')}
        </span>
      </div>
      <div className="anch-zone">{num(lo, 2)}–{num(hi, 2)} €</div>
      <p className="anch-plain">
        <Term t="fer-zona">{t('ab.ferZonaWord')}</Term> {t('ab.plainZone')}
      </p>
      <div className="anch-band">
        <div className="anch-axis" />
        <div className="anch-fill" style={{ left: `${P(lo)}%`, width: `${P(hi) - P(lo)}%` }} />
        <div className="anch-lbl" style={{ left: `${P(lo)}%` }}>{num(lo, zoneDec(hi))}</div>
        <div className="anch-lbl" style={{ left: `${P(hi)}%` }}>{num(hi, zoneDec(hi))}</div>
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
      {rec.one_off_note && (
        <div className="anch-proforma">
          <div className="prof-klabel">{t('ab.ooWhyH')}</div>
          <p>{tx(rec.one_off_note, lang)}</p>
        </div>
      )}
      {rec.pro_forma_note && (
        <div className="anch-proforma">
          <div className="prof-klabel">{t('ab.pfWhyH')}</div>
          <p>{tx(rec.pro_forma_note, lang)}</p>
        </div>
      )}
      {rec.reasoning && (
        <div className="anch-chain">
          <div className="prof-klabel">{t('ab.howAnchor')}</div>
          <p>{tx(rec.reasoning, lang)}</p>
          <div className="anch-chain-note">{t('ab.zoneExpl')}</div>
        </div>
      )}
      {(rec.qa_flags || []).length > 0 && (
        <div className="anch-qa">
          {rec.qa_flags.map((f, i) => {
            const pf = plainFlag(f, t)
            return (
              <div className="anch-qa-row" key={i}>
                <span className="flag">QA</span> {pf === f ? tx(f, lang) : pf}
              </div>
            )
          })}
        </div>
      )}
      {sotp && sotp.sotp_fair && sotp.sotp_market && (
        <div className="anch-sotp2">
          <div>
            <div className="prof-klabel">{t('ab.sotpMarket')}</div>
            <div className="anch-sotp2-v" style={{ color: PINE }}>
              {num(sotp.sotp_market.base_per_share, 2)} €
            </div>
            <div className="anch-sotp2-n">{tx(sotp.sotp_market.note, lang)} {t('ab.sotpAnchor')}</div>
          </div>
          <div>
            <div className="prof-klabel">{t('ab.sotpFair')}</div>
            <div className="anch-sotp2-v">
              {num(sotp.sotp_fair.base_per_share, 2)} €
              {sotp.our_vs_market_pct !== null && sotp.our_vs_market_pct !== undefined && (
                <span className="anch-sotp2-d" style={{ color: sotp.our_vs_market_pct >= 0 ? PINE : OX }}>
                  {' '}({sotp.our_vs_market_pct >= 0 ? '+' : ''}{num(sotp.our_vs_market_pct, 1)}%)
                </span>
              )}
            </div>
            <div className="anch-sotp2-n">{tx(sotp.sotp_fair.note, lang)}</div>
          </div>
        </div>
      )}
      <FairSotpBreakdown sotp={sotp} />
    </div>
  )
}

/* M51.4: mali raspis USPOREDNOG SOTP-a po dionici — čitatelj vidi kako od
   procjena kćeri (× vlasnički udio) nastaje broj, bez računanja napamet.
   Sve iz postojećeg exporta (identity: our_per_share za uvrštene, per_share
   za ostalo); završni red je autoritativna brojka iz sotp_fair. */
function FairSotpBreakdown({ sotp }) {
  const { lang, t } = useLang()
  if (!sotp || !sotp.sotp_fair || !sotp.identity) return null
  const listed = sotp.identity.filter((r) => r.listed && r.our_per_share != null)
  if (!listed.length) return null   // bez uvrštenih kćeri nema razlike vs glavni
  const isCash = (r) => (r.item || '').startsWith('neto novac')
  const isDisc = (r) => (r.item || '').startsWith('holding diskont')
  const othersPs = sotp.identity
    .filter((r) => !r.listed && !isCash(r) && !isDisc(r) && r.per_share != null)
    .reduce((a, r) => a + r.per_share, 0)
  const cashRow = sotp.identity.find(isCash)
  const dr = sotp.holding_discount_range || [0, 0]
  const disc = (dr[0] + dr[1]) / 2
  const subtotal = listed.reduce((a, r) => a + r.our_per_share, 0)
    + othersPs + (cashRow?.per_share || 0)
  return (
    <details className="anch-fairbrk">
      <summary>{t('ab.fairBreakH')}</summary>
      <table>
        <tbody>
          {listed.map((r) => (
            <tr key={r.item}>
              <td>{tx(r.item, lang)} <span className="basis">({t('ab.fairBreakOur')} × {num(r.pct * 100, 1)}% {t('ab.fairBreakStake')})</span></td>
              <td className="num">{num(r.our_per_share, 0)} €</td>
            </tr>
          ))}
          <tr>
            <td>{t('ab.fairBreakOthers')}</td>
            <td className="num">{num(othersPs, 0)} €</td>
          </tr>
          {cashRow && (
            <tr>
              <td>{t('ab.fairBreakCash')}</td>
              <td className="num">{num(cashRow.per_share, 0)} €</td>
            </tr>
          )}
          {disc > 0 && (
            <tr>
              <td>{t('ab.fairBreakDisc')} ({num(disc * 100, 1)}%)</td>
              <td className="num">−{num(subtotal * disc, 0)} €</td>
            </tr>
          )}
          <tr className="sotp-total">
            <td>{t('ab.fairBreakTotal')}</td>
            <td className="num">{num(sotp.sotp_fair.base_per_share, 2)} €</td>
          </tr>
        </tbody>
      </table>
      <div className="anch-sotp2-n">{t('ab.fairBreakNote')}</div>
    </details>
  )
}

export function SecondaryList({ data }) {
  const { lang, t } = useLang()
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
      <div className="sec-list-h">{t('ab.secondaryH')}</div>
      {secs.map((m) => {
        const r = rec.method_roles[m.key]
        const dev = r.vs_zone_pct
        return (
          <div className="sec-list-row" key={m.key}>
            <span className="sec-list-name">
              {METHOD_TERM[m.key]
                ? <Term t={METHOD_TERM[m.key]}>{methodShort(m.key, t, tx(m.label, lang))}</Term>
                : methodShort(m.key, t, tx(m.label, lang))}
            </span>
            <span className="sec-list-val">
              {num(m.base, 2)} €{dev ? ` (${dev > 0 ? '+' : ''}${num(dev * 100, 0)}%)` : ''}
            </span>
            <span className="sec-list-note">
              {tx(r.note, lang)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export function Risks({ risks }) {
  const { lang, t } = useLang()
  if (!risks || !risks.cards.length) return null
  return (
    <>
      <h3 className="prof-h3" style={{ marginBottom: 4 }}>{t('ab.risksH')}</h3>
      <p className="risk-sub">{tx(risks.note, lang)}</p>
      <div className="risk-grid">
        {risks.cards.map((c) => (
          <div className="risk-card" key={c.l}>
            <div className="risk-l">{tx(c.l, lang)}</div>
            <div className="risk-t">{tx(c.txt, lang)}</div>
          </div>
        ))}
      </div>
    </>
  )
}

/* graf financija po dizajnu: prihod = obrisi barova (steel), EBITDA = linija (borova) */
export function FinChart({ trend }) {
  const { lang, t } = useLang()
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
        <span className="prof-klabel">{tx(trend.revenue_label, lang).toUpperCase()} {t('ab.andEbitdaMln')}</span>
        <span className="prof-legend" style={{ fontSize: 10 }}>
          <i style={{ display: 'inline-block', width: 12, height: 8,
            background: 'rgba(47,93,134,0.28)', border: `1px solid ${STEEL}` }} /> {tx(trend.revenue_label, lang).toLowerCase()}
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
        {tx(trend.narration, lang)}
      </div>
    </div>
  )
}
