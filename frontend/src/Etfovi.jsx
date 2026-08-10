import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { IndexChart } from './Indeksi.jsx'
import { eur, fmtDate, num } from './format.js'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'

export function useEtfovi() {
  const [d, setD] = useState(null)
  useEffect(() => {
    fetch('/data/etfovi.json').then((r) => r.json()).then(setD)
      .catch(() => setD({ rows: [], as_of: null }))
  }, [])
  return d
}

/* M63: /etf-ovi — svi ETF-ovi uvršteni na ZSE. Činjenice: ime fonda, indeks
   koji prati (iz službenih EHO objava izdavatelja), zadnja cijena/promet,
   likvidnost i graf. ETF replicira indeks pa se fer-vrijednost analiza NE
   izrađuje — gdje indeks pratimo (ZSE), prikazuje se i njegova vrijednost.
   Podaci: /data/etfovi.json (build_etfovi.py). */

export function EtfoviIndex() {
  const { lang, t } = useLang()
  const d = useEtfovi()
  const [sel, setSel] = useState(null)
  useEffect(() => {
    document.title = `${t('etf.pageTitle')} · Burzovni list`
  }, [lang])
  const rows = useMemo(() => d?.rows || [], [d])
  const r = rows.find((x) => x.symbol === sel) || null
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>{t('etf.pageTitle')}</h1>
          <span>{t('etf.subtitle')}{d?.as_of ? ` · ${t('bond.lastTrade')} ${fmtDate(d.as_of)}` : ''}</span></div>
        {!d ? <div className="loading">{t('common.loading')}</div> : (
          <div className="mk-scroll">
            <table>
              <thead><tr>
                <th>{t('etf.colSymbol')}</th><th>{t('etf.colFund')}</th>
                <th>{t('etf.colIndex')}</th><th className="num">{t('etf.colPrice')}</th>
                <th className="num">{t('etf.colChange')}</th>
                <th className="num">{t('etf.colTurnover')}</th>
                <th className="num">{t('etf.colLiquidity')}</th>
              </tr></thead>
              <tbody>
                {rows.map((x) => (
                  <tr key={x.symbol} onClick={() => setSel(sel === x.symbol ? null : x.symbol)}
                    style={{ cursor: 'pointer' }} className={sel === x.symbol ? 'on' : ''}>
                    <td><Link to={lang === 'en' ? `/en/etf/${x.symbol.toLowerCase()}` : `/etf/${x.symbol.toLowerCase()}`}
                      onClick={(e) => e.stopPropagation()}><b>{x.symbol}</b></Link>
                      {x.stale && <i className="mk-ill" title={t('etf.staleTitle')}> {t('mkt.illiq')}</i>}</td>
                    <td>{x.name ? tx(x.name, lang) : <span className="flag">{t('bond.masterInProgress')}</span>}
                      <div className="fund-src">{x.category ? tx(x.category, lang) : ''}
                        {x.listed_since ? ` · ${t('etf.listedSince')} ${fmtDate(x.listed_since)}` : ''}</div></td>
                    <td>{x.index_name ? tx(x.index_name, lang) : t('common.na')}
                      {x.index_data && (
                        <div className="fund-src">
                          {num(x.index_data.last_value, 2)}
                          {x.index_data.change_pct !== null && x.index_data.change_pct !== undefined
                            ? ` (${x.index_data.change_pct > 0 ? '+' : ''}${num(x.index_data.change_pct, 2)} %)` : ''}
                        </div>
                      )}</td>
                    <td className="num">{x.last_close_eur !== null && x.last_close_eur !== undefined
                      ? eur(x.last_close_eur, 2) : t('common.na')}
                      {x.last_date && <div className="fund-src">{fmtDate(x.last_date)}</div>}</td>
                    <td className="num">{x.change_pct !== null && x.change_pct !== undefined
                      ? `${x.change_pct > 0 ? '+' : ''}${num(x.change_pct, 2)} %` : '—'}</td>
                    <td className="num">{x.last_turnover_eur
                      ? eur(x.last_turnover_eur, 0) : '—'}</td>
                    <td className="num">{x.traded_days_1y}/{x.liq_workdays || x.workdays_1y}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {r && (
          <section style={{ marginTop: 24 }}>
            <div className="sec-label">{r.symbol} — {r.name ? tx(r.name, lang) : t('bond.masterInProgress')}</div>
            <div className="kv" style={{ marginBottom: 16 }}>
              <div className="cell"><div className="k">ISIN</div>
                <div className="v mono" style={{ fontSize: 14 }}>{r.isin}</div>
                <div className="n">{r.issuer || ''}</div></div>
              <div className="cell"><div className="k">{t('etf.tracksIndex')}</div>
                <div className="v" style={{ fontSize: 14 }}>{r.index_name ? tx(r.index_name, lang) : t('common.na')}</div>
                {r.index_data?.slug && (
                  <div className="n">
                    <Link to={lang === 'en' ? `/en/index/${r.index_data.slug}` : `/indeks/${r.index_data.slug}`}>
                      {t('etf.indexDataLink')}
                    </Link>
                  </div>
                )}</div>
              <div className="cell"><div className="k">{t('etf.colPrice')}</div>
                <div className="v">{r.last_close_eur !== null && r.last_close_eur !== undefined
                  ? eur(r.last_close_eur, 2) : t('common.na')}</div>
                <div className="n">{r.last_date ? `EOD ${fmtDate(r.last_date)}` : ''}</div></div>
              <div className="cell"><div className="k">{t('etf.colLiquidity')}</div>
                <div className="v">{r.traded_days_1y}/{r.liq_workdays || r.workdays_1y}</div>
                <div className="n">{t('etf.liquidityNote')}</div></div>
            </div>
            {r.series?.length > 1 && (
              <IndexChart series={r.series.map((p) => ({ date: p.date, value: p.close_eur }))}
                label={`${r.symbol} · EUR`} />
            )}
            <p className="fund-src" style={{ marginTop: 8 }}>{t('etf.srcLabel')} {tx(r.source, lang)}</p>
            <p><Link to={lang === 'en' ? `/en/etf/${r.symbol.toLowerCase()}` : `/etf/${r.symbol.toLowerCase()}`}>
              {t('etf.detailLink')} →</Link></p>
          </section>
        )}
        <div className="disc" style={{ marginTop: 24 }}>
          {d?.note ? tx(d.note, lang) : t('etf.disc')}
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}

/* M64: /etf/<oznaka> — stranica fonda: opis, naknade (TER), pokazatelji
   portfelja (P/E ili dospijeće/duracija/prinos), deset najvećih pozicija
   (ZSE tickeri vode na našu analizu), prinosi po razdobljima i graf. */
const HTYPE_KEY = {
  Dionica: 'etf.h.stock', Obveznica: 'etf.h.bond',
  'Trezorski zapis': 'etf.h.tbill', Depozit: 'etf.h.deposit',
  'Račun': 'etf.h.account', 'Novac i ostalo': 'etf.h.cash',
  Ostalo: 'etf.h.other',
}

export function EtfDetail() {
  const { symbol } = useParams()
  const d = useEtfovi()
  const { lang, t } = useLang()
  const r = d?.rows?.find((x) => x.symbol.toLowerCase() === symbol)
  useEffect(() => {
    if (r) document.title = `${r.symbol} ETF · Burzovni list`
  }, [r, lang])
  const f = r?.facts || null
  const pi = f?.portfolio_indicators || null
  const fees = f?.fees_pct || null
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        {!d ? <div className="loading">{t('common.loading')}</div>
          : !r ? (
            <section><div className="mk-title"><h1>{t('etf.notFound')}</h1></div>
              <p className="imp-p"><Link to={lang === 'en' ? '/en/etfs' : '/etf-ovi'}>← {t('etf.all')}</Link></p></section>
          ) : (
            <>
              <div className="mk-title">
                <h1>{r.symbol} — {r.name ? tx(r.name, lang) : t('bond.masterInProgress')}</h1>
                <span>{r.isin} · {r.issuer || ''}{r.stale ? ` · ${t('bond.priceIndicative')}` : ''}</span>
              </div>
              {r.desc && <p className="imp-p">{lang === 'en' ? r.desc.en : r.desc.hr}</p>}
              <div className="kv" style={{ marginBottom: 16 }}>
                <div className="cell"><div className="k">{t('etf.colPrice')}</div>
                  <div className="v">{r.last_close_eur !== null && r.last_close_eur !== undefined ? eur(r.last_close_eur, 2) : t('common.na')}</div>
                  <div className="n">{r.last_date ? `EOD ${fmtDate(r.last_date)}` : ''}</div></div>
                {f?.unit_value !== undefined && f?.unit_value !== null && (
                  <div className="cell"><div className="k">{t('etf.unitValue')}</div>
                    <div className="v">{eur(f.unit_value, 2)}</div>
                    <div className="n">{t('etf.monthlyReport')} {r.facts_period || ''}</div></div>
                )}
                {f?.nav_meur !== undefined && f?.nav_meur !== null && (
                  <div className="cell"><div className="k">NAV</div>
                    <div className="v">{num(f.nav_meur, 1)} M€</div>
                    <div className="n">{t('etf.monthlyReport')} {r.facts_period || ''}</div></div>
                )}
                {fees && (
                  <div className="cell"><div className="k">TER</div>
                    <div className="v">{num(fees.ter, 2)} %</div>
                    <div className="n">{t('etf.terNote')}</div></div>
                )}
                <div className="cell"><div className="k">{t('etf.tracksIndex')}</div>
                  <div className="v" style={{ fontSize: 14 }}>{r.index_name ? tx(r.index_name, lang) : t('common.na')}</div>
                  {r.index_data?.slug && (
                    <div className="n"><Link to={lang === 'en' ? `/en/index/${r.index_data.slug}` : `/indeks/${r.index_data.slug}`}>{t('etf.indexDataLink')}</Link></div>
                  )}</div>
                <div className="cell"><div className="k">{t('etf.colLiquidity')}</div>
                  <div className="v">{r.traded_days_1y}/{r.liq_workdays || r.workdays_1y}</div>
                  <div className="n">{(r.liq_workdays || 250) < 250 ? t('etf.liqSinceListing') : t('etf.liquidityNote')}</div></div>
                {r.listed_since && (
                  <div className="cell"><div className="k">{t('etf.listedSinceH')}</div>
                    <div className="v" style={{ fontSize: 15 }}>{fmtDate(r.listed_since)}</div>
                    <div className="n">{r.listed_since_src === 'factsheet' ? t('etf.listedSrcFs') : t('etf.listedSrcSeries')}</div></div>
                )}
              </div>
              {pi && (
                <section style={{ marginBottom: 16 }}>
                  <div className="sec-label">{t('etf.piH')}</div>
                  <div className="kv">
                    {pi.kind === 'equity' ? (
                      <>
                        <div className="cell"><div className="k">P/E</div>
                          <div className="v">{num(pi.pe, 1)}</div>
                          <div className="n">{t('etf.piPe')}</div></div>
                        <div className="cell"><div className="k">{t('etf.piDy')}</div>
                          <div className="v">{num(pi.div_yield_pct, 1)} %</div></div>
                        <div className="cell"><div className="k">ROE</div>
                          <div className="v">{num(pi.roe_pct, 1)} %</div></div>
                      </>
                    ) : (
                      <>
                        <div className="cell"><div className="k">{t('etf.piMat')}</div>
                          <div className="v">{num(pi.avg_maturity, 2)}</div>
                          <div className="n">{pi.unit === 'godine' ? t('etf.years') : t('etf.months')}</div></div>
                        <div className="cell"><div className="k">{t('etf.piDur')}</div>
                          <div className="v">{num(pi.mod_duration, 2)}</div>
                          <div className="n">{pi.unit === 'godine' ? t('etf.years') : t('etf.months')}</div></div>
                        <div className="cell"><div className="k">{t('etf.piYtm')}</div>
                          <div className="v">{num(pi.avg_ytm_pct, 2)} %</div>
                          <div className="n">{t('etf.ytmNote')}</div></div>
                      </>
                    )}
                  </div>
                  <p className="fund-src">{t('etf.factsSrc')} {r.facts_period || ''}{r.facts_source_url ? <> · <a href={r.facts_source_url} target="_blank" rel="noreferrer">EHO</a></> : null}</p>
                </section>
              )}
              {f?.holdings?.length > 0 && (
                <section style={{ marginBottom: 16 }}>
                  <div className="sec-label">{t('etf.holdingsH')}</div>
                  <table>
                    <thead><tr><th>{t('etf.hType')}</th><th>{t('etf.hName')}</th><th className="num">{t('etf.hWeight')}</th></tr></thead>
                    <tbody>
                      {f.holdings.map((h, i) => (
                        <tr key={i}>
                          <td className="basis">{HTYPE_KEY[h.type] ? t(HTYPE_KEY[h.type]) : h.type}</td>
                          <td>{h.zse && h.ticker
                            ? <Link to={lang === 'en' ? `/en/stock/${h.ticker.toLowerCase()}` : `/dionica/${h.ticker.toLowerCase()}`}>{h.name}</Link>
                            : h.name}</td>
                          <td className="num">{num(h.weight_pct, 1)} %</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}
              {fees && (
                <section style={{ marginBottom: 16 }}>
                  <div className="sec-label">{t('etf.feesH')}</div>
                  <table>
                    <tbody>
                      <tr><td>{t('etf.feeMgmt')}</td><td className="num">{num(fees.management, 2)} %</td></tr>
                      <tr><td>{t('etf.feeDep')}</td><td className="num">{num(fees.depositary, 2)} %</td></tr>
                      <tr><td>{t('etf.feeOther')}</td><td className="num">{num(fees.other, 2)} %</td></tr>
                      <tr><td><b>{t('etf.feeTer')}</b></td><td className="num"><b>{num(fees.ter, 2)} %</b></td></tr>
                      <tr><td>{t('etf.feeTrans')}</td><td className="num">{num(fees.transaction, 2)} %</td></tr>
                    </tbody>
                  </table>
                  <p className="fund-src">{t('etf.feesNote')}</p>
                </section>
              )}
              {f?.performance?.length > 0 && (
                <section style={{ marginBottom: 16 }}>
                  <div className="sec-label">{t('etf.perfH')}</div>
                  <table>
                    <thead><tr><th>{t('etf.perfPeriod')}</th><th className="num">{t('etf.perfFund')}</th><th className="num">Benchmark</th></tr></thead>
                    <tbody>
                      {f.performance.map((p, i) => (
                        <tr key={i}>
                          <td>{tx(p.period, lang)}</td>
                          <td className="num">{num(p.fund_pct, 2)} %</td>
                          <td className="num">{p.benchmark_pct !== null && p.benchmark_pct !== undefined ? `${num(p.benchmark_pct, 2)} %` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="fund-src">{t('etf.perfNote')}</p>
                </section>
              )}
              {r.series?.length > 1 && (
                <IndexChart series={r.series.map((p) => ({ date: p.date, value: p.close_eur }))}
                  label={`${r.symbol} · EUR (ZSE)`} />
              )}
              <div className="disc" style={{ marginTop: 24 }}>
                {d?.note ? tx(d.note, lang) : t('etf.disc')}
              </div>
            </>
          )}
      </main>
      <SiteFooter />
    </div>
  )
}
