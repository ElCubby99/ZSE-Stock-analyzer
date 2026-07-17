import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { fmtDate, num } from './format.js'
import { useLang } from './i18n/LangContext.jsx'

/* M-FOND: /mirovinski-fondovi — vrijednosti obračunskih jedinica OMF-ova
   (A/B/C) i Mirex (izvor HANFA, MJESEČNI ritam) + sinergija s našim
   podacima: ZSE dionice u čijim se top-10 popisima pojavljuju OMF-ovi.
   BEZ rangiranja fondova (abecedni redoslijed) — činjenični prikaz. */

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
            {['A', 'B', 'C'].map((cat) => (
              <section key={cat} style={{ marginTop: 14 }}>
                <div className="sec-label">{t('fund.category')} {cat}</div>
                <div className="mk-scroll">
                <table>
                  <thead><tr><th>{t('fund.fund')}</th><th className="num">{t('fund.unit')}</th>
                    <th className="num">YTD</th><th className="num">{t('fund.y1')}</th>
                    <th className="num">{t('fund.y3')}</th><th className="num">{t('fund.y5')}</th>
                    <th>{t('fund.date')}</th></tr></thead>
                  <tbody>
                    {d.units.filter((u) => u.category === cat).map((u) => (
                      <tr key={u.fund}>
                        <td>{u.fund} OMF — {t('fund.catLabel')} {cat}</td>
                        <td className="num">{u.unit_value !== null && u.unit_value !== undefined
                          ? num(u.unit_value, 4) : <span className="np">{t('fund.awaitingImport')}</span>}</td>
                        <td className="num">{pct(u.ytd, na)}</td>
                        <td className="num">{pct(u.y1, na)}</td>
                        <td className="num">{pct(u.y3, na)}</td>
                        <td className="num">{pct(u.y5, na)}</td>
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
                          <td className="num" colSpan={3} />
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
