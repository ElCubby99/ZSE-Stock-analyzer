import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { IndexChart } from './Indeksi.jsx'
import { eur, fmtDate, num } from './format.js'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'

/* M63: /etf-ovi — svi ETF-ovi uvršteni na ZSE. Činjenice: ime fonda, indeks
   koji prati (iz službenih EHO objava izdavatelja), zadnja cijena/promet,
   likvidnost i graf. ETF replicira indeks pa se fer-vrijednost analiza NE
   izrađuje — gdje indeks pratimo (ZSE), prikazuje se i njegova vrijednost.
   Podaci: /data/etfovi.json (build_etfovi.py). */

export function EtfoviIndex() {
  const { lang, t } = useLang()
  const [d, setD] = useState(null)
  const [sel, setSel] = useState(null)
  useEffect(() => {
    fetch('/data/etfovi.json').then((r) => r.json()).then(setD)
      .catch(() => setD({ rows: [], as_of: null }))
  }, [])
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
                    <td><b>{x.symbol}</b>
                      {x.stale && <i className="mk-ill" title={t('etf.staleTitle')}> {t('mkt.illiq')}</i>}</td>
                    <td>{x.name ? tx(x.name, lang) : <span className="flag">{t('bond.masterInProgress')}</span>}
                      {x.category && <div className="fund-src">{tx(x.category, lang)}</div>}</td>
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
                    <td className="num">{x.traded_days_1y}/{x.workdays_1y}</td>
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
                <div className="v">{r.traded_days_1y}/{r.workdays_1y}</div>
                <div className="n">{t('etf.liquidityNote')}</div></div>
            </div>
            {r.series?.length > 1 && (
              <IndexChart series={r.series.map((p) => ({ date: p.date, value: p.close_eur }))}
                label={`${r.symbol} · EUR`} />
            )}
            <p className="fund-src" style={{ marginTop: 8 }}>{t('etf.srcLabel')} {tx(r.source, lang)}</p>
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
