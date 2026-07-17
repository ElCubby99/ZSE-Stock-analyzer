import React, { useState } from 'react'
import { Term } from './Legend.jsx'
import { GapCell, useOverview } from './Shell.jsx'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'
import { sectorLabel } from './sectorLabels.mjs'
import { dash, eur, fmtDate, meur, num, pct } from './format.js'

/* Tab-struktura stranice dionice (dizajn 4). Sve iz postojećih podataka;
   BEZ 'tehničke analize' i BEZ ratinga/ocjena (MAR). */

export const TABS = [
  ['pregled', 'stock.tab.overview'],
  ['analiza', 'stock.tab.valuation'],
  ['pokazatelji', 'stock.tab.indicators'],
  ['usporedba', 'stock.tab.comparison'],
  ['izvjestaji', 'stock.tab.reports'],
  ['dionicari', 'stock.tab.shareholders'],
  ['novosti', 'stock.tab.news'],
]

export function TabBar({ tab, setTab, ticker }) {
  const { lang, t } = useLang()
  const finHref = lang === 'en'
    ? `/en/stock/${String(ticker).toLowerCase()}/financials`
    : `/dionica/${String(ticker).toLowerCase()}/financije`
  return (
    <div className="stab">
      {TABS.map(([k, key]) => (
        <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{t(key)}</button>
      ))}
      {/* M37: FINANCIJE je zasebna ruta (as-reported izvještaji, SSG) */}
      {ticker && (
        <a className="stab-link" href={finHref}>
          {t('stock.tab.financials')} ↗
        </a>
      )}
    </div>
  )
}

/* M18: puni set pokazatelja (≥ investiramo.com) — 10 kartica, TTM/kvartalni
   sloj. Sve izvedenice su DETERMINISTIČKI izračun (src/indicators.py), ne
   procjena. Osnovica (basis) je uvijek vidljiva (TTM > FY-s-oznakom > n/p);
   FY se NIKAD ne prikazuje kao TTM. Formula je u tooltipu; n/p nosi razlog. */
function fmtIndVal(it, lang) {
  const { v, unit } = it
  /* note za 'date' je ISO datum ili tekst ('n/p') — datum lokaliziramo,
     tekst ide kroz podatkovni prijevod */
  const dateNote = () => (it.note
    ? (/^\d{4}-\d{2}-\d{2}$/.test(it.note) ? fmtDate(it.note) : tx(it.note, lang))
    : null)
  if (v === null || v === undefined) {
    return unit === 'date' ? dateNote() : null
  }
  switch (unit) {
    case '%': return pct(v, 1)
    case 'x': return `${num(v, 2)}×`
    case 'meur': return meur(v, 1)
    case 'eur': return eur(v, 0)
    case 'days': return `${num(v, 0)} d`
    case 'count': return num(v, 0)
    case 'date': return dateNote() || dash
    default: return num(v, 2)
  }
}

function shortBasis(b) {
  if (!b) return ''
  if (b.startsWith('TTM')) {
    const m = b.match(/do (\d{2}\.\d{2}\.)(\d{4})/)
    return m ? `TTM →${m[1]}${m[2].slice(2)}` : 'TTM'
  }
  if (b.startsWith('Kvartalno')) {
    const m = b.match(/(\d{2}\.\d{2}\.)(\d{4})/)
    return m ? `Q ${m[1]}${m[2].slice(2)}` : 'Q'
  }
  const fy = b.match(/FY(\d{4})/)
  if (fy) return `FY${fy[1].slice(2)}`
  const eod = b.match(/EOD do (\d{4})-(\d{2})-(\d{2})/)
  if (eod) return `${eod[3]}.${eod[2]}.${eod[1].slice(2)}`
  return b.length > 14 ? `${b.slice(0, 13)}…` : b
}

export function IndicatorGroups({ indicators }) {
  /* balončić radi i NA DODIR (mobitel): native title postoji samo na
     hover, pa klik/tap na naziv otvara redak s objašnjenjem ispod
     pokazatelja — isto objašnjenje, dva ulaza (hover title + tap). */
  const { lang, t } = useLang()
  const [open, setOpen] = useState(null)
  if (!indicators || !indicators.groups) return null
  const finHref = indicators.ticker && (lang === 'en'
    ? `/en/stock/${String(indicators.ticker).toLowerCase()}/financials`
    : `/dionica/${String(indicators.ticker).toLowerCase()}/financije`)
  return (
    <section>
      <div className="sec-label">{t('ind.secLabel')}</div>
      <div className="ind-grid">
        {indicators.groups.map((g) => (
          <div className="ind-card" key={g.key}>
            <h4>{tx(g.title, lang)}</h4>
            <table className="ind-tbl"><tbody>
              {g.items.map((it, i) => {
                const val = fmtIndVal(it, lang)
                const np = val === null
                /* formula + "Zašto ovako" reasoning (dvorazinski princip —
                   brojka odmah, obrazloženje izbora iza hovera/dodira) */
                const hint = [
                  it.formula ? `${t('ind.formula')}: ${tx(it.formula, lang)}` : null,
                  it.why ? `${t('ind.why')}: ${tx(it.why, lang)}` : null,
                ].filter(Boolean).join('\n\n')
                const rk = `${g.key}:${i}`
                const isOpen = open === rk
                return (
                  <React.Fragment key={i}>
                  <tr>
                    <td className="ind-k">
                      <span title={hint} className={hint ? 'ind-hint' : ''}
                        onClick={() => hint && setOpen(isOpen ? null : rk)}>
                        {tx(it.k, lang)}{it.why ? <sup className="ind-why">?</sup> : null}
                      </span>
                    </td>
                    <td className="ind-v num">
                      {np ? (
                        <span className="np" title={tx(it.np_reason, lang) || ''}
                          onClick={() => it.np_reason && setOpen(isOpen ? null : rk)}>{t('common.na')}</span>
                      ) : (
                        <>
                          <b>{val}</b>
                          {it.basis && (
                            <span className="ind-basis" title={tx(it.basis, lang)}>{shortBasis(it.basis)}</span>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                  {isOpen && (hint || it.np_reason) && (
                    <tr className="ind-poprow">
                      <td colSpan={2}>
                        {it.formula && <div><b>{t('ind.formula')}:</b> {tx(it.formula, lang)}</div>}
                        {it.why && <div><b>{t('ind.why')}:</b> {tx(it.why, lang)}</div>}
                        {np && it.np_reason && <div><b>{t('common.na')}:</b> {tx(it.np_reason, lang)}</div>}
                        {it.basis && <div className="dim">{t('ind.basis')}: {tx(it.basis, lang)}</div>}
                      </td>
                    </tr>
                  )}
                  </React.Fragment>
                )
              })}
            </tbody></table>
          </div>
        ))}
      </div>
      {indicators.review_flags && indicators.review_flags.length > 0 && (
        <div className="subnote"><span className="flag">{t('ind.forReview')}</span>{' '}
          {indicators.review_flags.map((f) => tx(f, lang)).join('; ')}.</div>
      )}
      <div className="subnote">
        {tx(indicators.note, lang)} {t('ind.legendIntro')} <b>TTM →dd.mm.</b> {t('ind.legendTtm')}{' '}
        <b>FYgg</b> {t('ind.legendFy')} <b>Q dd.mm.</b> {t('ind.legendQ')}{' '}
        {t('ind.legendDerived1')} <sup>?</sup>{t('ind.legendDerived2')}{' '}
        <span className="np">{t('common.na')}</span> {t('ind.npCarries')}
        {finHref && (
          <> {t('ind.backing')} <a href={finHref}>{t('ind.fullReports')}</a></>
        )}
      </div>
    </section>
  )
}

/* Ključni pokazatelji: tržišni omjeri + POLOŽAJ NASPRAM FER-ZONE (fer P/E =
   sredina sidrene zone / EPS; fer P/B analogno) — činjenica, ne ocjena. */
export function KeyIndicators({ data }) {
  const { t } = useLang()
  const rec = data.valuation?.reconciliation
  const m = data.metrics || {}
  const zoneMid = rec && rec.zone_low !== null ? (rec.zone_low + rec.zone_high) / 2 : null
  const ferPe = zoneMid && m.eps > 0 ? zoneMid / m.eps : null
  const ferPb = zoneMid && m.bvps > 0 ? zoneMid / m.bvps : null
  const rows = (m.per_class || []).map((c) => ({
    t: c.class_ticker, price: c.price, pe: c.pe, pb: c.pb, dy: c.div_yield,
  }))
  return (
    <section>
      <div className="sec-label">{t('ki.secLabel')}</div>
      <table>
        <thead><tr><th>{t('ki.class')}</th><th className="num">{t('ki.priceEur')}</th>
          <th className="num"><Term t="P/E">P/E</Term></th>
          <th className="num"><Term t="P/E">{t('ki.fairPe')}</Term></th>
          <th className="num"><Term t="P/B">P/B</Term></th>
          <th className="num"><Term t="P/B">{t('ki.fairPb')}</Term></th>
          <th className="num">{t('ki.divYield')}</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.t}>
              <td><b>{r.t}</b></td>
              <td className="num">{r.price === null ? dash : num(r.price, 2)}</td>
              <td className="num">{r.pe === null ? dash : num(r.pe, 1)}</td>
              <td className="num pine-t">{ferPe === null ? dash : num(ferPe, 1)}</td>
              <td className="num">{r.pb === null ? dash : num(r.pb, 2)}</td>
              <td className="num pine-t">{ferPb === null ? dash : num(ferPb, 2)}</td>
              <td className="num">{r.dy ? pct(r.dy, 2) : dash}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="subnote">
        {t('ki.note1')}{rec && rec.zone_low !== null
          ? `${num(rec.zone_low, 0)}–${num(rec.zone_high, 0)} €` : dash}{t('ki.note2')}
      </div>
    </section>
  )
}

/* Usporedba: dionica vs klase ISTOG sektora (overview.json — stvarni podaci);
   valuacijski peer skup (docs/peers.md) citiran iz params.sources. */
/* Z4: horizontalni multipl-graf — raspon sektora, medijan, pozicija naše
   dionice; iz STVARNIH domaćih podataka (overview) */
function MultipleBar({ label, rows, mine, field, fmt }) {
  const { t } = useLang()
  const vals = rows.map((s) => s[field]).filter((v) => v !== null && v !== undefined && v > 0)
  if (vals.length < 3) return null
  const sorted = [...vals].sort((a, b) => a - b)
  const med = sorted[Math.floor(sorted.length / 2)]
  const ours = rows.filter((s) => mine.has(s.ticker) && s[field] > 0).map((s) => s[field])
  const lo = sorted[0]; const hi = sorted[sorted.length - 1]
  const P = (v) => Math.max(1, Math.min(99, ((v - lo) / (hi - lo || 1)) * 100))
  return (
    <div className="cmp-mbar">
      <span className="cmp-mbar-k">{label}</span>
      <div className="mk-band" style={{ height: 14 }}>
        <div className="mk-band-axis" />
        <div className="mk-band-tick" style={{ left: `${P(med)}%`, background: '#1F6E5A' }}
          title={`${t('cmpS.median')} ${fmt(med)}`} />
        {ours.map((v, i) => (
          <div key={i} className="mk-band-tick" style={{ left: `${P(v)}%`, background: '#9E2B25' }}
            title={`${t('cmpS.thisStock')} ${fmt(v)}`} />
        ))}
      </div>
      <span className="cmp-mbar-v mono">med {fmt(med)}{ours.length ? ` · ${t('cmpS.us')} ${fmt(ours[0])}` : ''}</span>
    </div>
  )
}

function GlobalPeers({ gp }) {
  const { lang, t } = useLang()
  if (!gp) return null
  return (
    <section>
      <div className="sec-label">{t('gp.secLabel')}</div>
      <table>
        <thead><tr><th>Peer</th><th>{t('gp.level')}</th><th>{t('gp.market')}</th>
          {gp.has_metrics && gp.metrics_set.map((m) => <th key={m} className="num">{m.toUpperCase()}</th>)}
        </tr></thead>
        <tbody>
          {gp.peers.map((p) => (
            <tr key={p.name}>
              <td><b>{p.name}</b>{p.ticker && <span className="fund-src"> {p.ticker}</span>}</td>
              <td>{tx(gp.levels_hr[p.level] || p.level, lang)}</td>
              <td className="fund-src">{p.market}</td>
              {gp.has_metrics && gp.metrics_set.map((m) => (
                <td key={m} className="num">{p.metrics?.[m] ?? dash}</td>))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="subnote">
        {tx(gp.note, lang)}.
        {gp.as_of ? ` ${t('gp.snapshot')} ${gp.as_of}.` : ''}
        {gp.no_metrics_reason ? ` ${tx(gp.no_metrics_reason, lang)}.` : ''}
      </div>
    </section>
  )
}

export function Comparison({ data }) {
  const { lang, t } = useLang()
  const ov = useOverview()
  if (!ov) return <div className="loading">{t('common.loading')}</div>
  const mine = new Set((data.share_classes || []).map((c) => c.ticker))
  const rows = ov.stocks.filter((s) => s.sector === data.sector)
  const peerSrc = data.valuation?.params?.sources?.peers
  const isFin = ['bank', 'insurance', 'fund'].includes(data.sector)
  return (
    <>
    <section>
      <div className="sec-label">
        {t('cmpS.secLabel')} {sectorLabel(data.sector, lang) || data.sector || dash}
      </div>
      {rows.length <= mine.size ? (
        <div className="subnote"><span className="np">{t('common.na')}</span> — {t('cmpS.noOthers')}</div>
      ) : (
        <div className="mk-scroll">
          <table>
            <thead><tr><th>{t('cmpS.stock')}</th><th className="num">{t('ki.priceEur')}</th><th className="num">P/E</th>
              <th className="num">P/B</th><th className="num">{t('cmpS.yield')}</th><th>{t('cmpS.gap')}</th></tr></thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.ticker} className={mine.has(s.ticker) ? 'cmp-self' : ''}>
                  <td><b>{s.ticker}</b> <span className="fund-src">{s.name}</span>
                    {mine.has(s.ticker) && <span className="okflag" style={{ marginLeft: 6 }}>{t('cmpS.thisStock')}</span>}</td>
                  <td className="num">{s.price === null ? dash : num(s.price, 2)}</td>
                  <td className="num">{s.pe === null || s.pe === undefined ? dash : num(s.pe, 1)}</td>
                  <td className="num">{s.pb === null || s.pb === undefined ? dash : num(s.pb, 2)}</td>
                  <td className="num">{s.div_yield ? pct(s.div_yield, 1) : dash}</td>
                  <td><GapCell s={s} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {rows.length > mine.size && (
        <div className="cmp-mbars">
          <MultipleBar label="P/E" rows={rows} mine={mine} field="pe" fmt={(v) => num(v, 1)} />
          <MultipleBar label="P/B" rows={rows} mine={mine} field="pb" fmt={(v) => num(v, 2)} />
          {isFin && <div className="subnote">{t('cmpS.finNote1')}
            {data.sector === 'bank' ? t('cmpS.finNoteBank') : t('cmpS.finNoteOther')}.</div>}
        </div>
      )}
      <div className="subnote">
        {t('cmpS.note')}
        {peerSrc ? <> {t('cmpS.peerSet')} {tx(peerSrc, lang)}</> : null}
      </div>
    </section>
    <GlobalPeers gp={data.global_peers} />
    </>
  )
}

export function NewsTab({ news }) {
  const { lang, t } = useLang()
  const items = news?.items || []
  return (
    <section>
      <div className="sec-label">{t('nt.secLabel')}</div>
      {!items.length ? (
        <div className="subnote"><span className="flag">{t('nt.emptyFlag')}</span>{' '}
          {t('nt.empty')}</div>
      ) : (
        <div className="news-list">
          {items.map((n, i) => (
            <a key={i} className="news-row" href={n.url} target="_blank" rel="noreferrer">
              <span className="news-date">{n.date || dash}</span>
              <span className="news-title">{n.title}</span>
            </a>
          ))}
        </div>
      )}
      <div className="subnote">{tx(news?.note, lang)}.</div>
    </section>
  )
}
