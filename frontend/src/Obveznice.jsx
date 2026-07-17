import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { IndexChart } from './Indeksi.jsx'
import { fmtDate, num } from './format.js'
import { useLang } from './i18n/LangContext.jsx'

/* M-BOND: /obveznice (sve uvrštene: državne/municipalne/korporativne;
   sort/filter) i /obveznica/<oznaka> (detalji + graf cijene + raspored
   kupona). Cijene su ČISTE, u % nominale (jasno označeno). Deterministička
   analiza prinosa (YTM/duracija/obračunata kamata — formule na
   /metodologija); bez fer-zone i bez preporuka. */

export function useObveznice() {
  const [d, setD] = useState(null)
  useEffect(() => {
    fetch('/data/obveznice.json').then((r) => r.json()).then(setD)
      .catch(() => setD({ rows: [], as_of: null }))
  }, [])
  return d
}

const pct = (v, d = 2) => (v === null || v === undefined ? '—' : `${num(v, d)} %`)

// btype vrijednosti u obveznice.json su hrvatske podatkovne konstante
// ('državna'…) — zapisane escapeom da u izvoru ne bude HR teksta;
// na ekran idu isključivo prevedene kroz btypeLabel().
const BTYPE_KEY = {
  'dr\u017eavna': 'bond.type.government',
  korporativna: 'bond.type.corporate',
  municipalna: 'bond.type.municipal',
}
const btypeLabel = (v, t) => (BTYPE_KEY[v] ? t(BTYPE_KEY[v]) : v)

const TYPES = [['sve', 'bond.type.all'],
  ...Object.entries(BTYPE_KEY)]

const COLS = [
  ['symbol', 'bond.col.symbol', 'l'], ['issuer', 'bond.col.issuer', 'l'],
  ['btype', 'bond.col.type', 'l'],
  ['maturity_date', 'bond.col.maturity', 'l'], ['coupon_pct', 'bond.col.coupon', 'r'],
  ['price_pct', 'bond.col.price', 'r'], ['ytm_pct', 'YTM', 'r'],
  ['duration', 'bond.col.duration', 'r'],
]

export function ObvezniceIndex() {
  const d = useObveznice()
  const { lang, t } = useLang()
  const [tip, setTip] = useState('sve')
  const [sk, setSk] = useState('maturity_date')
  const [dir, setDir] = useState(1)
  useEffect(() => {
    document.title = `${t('bond.pageTitle')} · Burzovni list`
  }, [lang])
  const rows = useMemo(() => {
    const list = (d?.rows || []).filter((r) => tip === 'sve' || r.btype === tip)
    const val = (r) => (sk === 'duration' ? r.duration?.modified : r[sk])
    return [...list].sort((a, b) => {
      const av = val(a); const bv = val(b)
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av ?? '').localeCompare(String(bv ?? '')) * dir
      }
      const an = av === null || av === undefined ? Infinity * dir : av
      const bn = bv === null || bv === undefined ? Infinity * dir : bv
      return (an - bn) * dir
    })
  }, [d, tip, sk, dir])
  const sort = (k) => () => { setDir(sk === k ? -dir : 1); setSk(k) }
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>{t('bond.pageTitle')}</h1>
          <span>{t('bond.subtitle')}{d?.as_of ? ` · ${t('bond.lastTrade')} ${fmtDate(d.as_of)}` : ''}</span></div>
        <div className="prof-chips" style={{ margin: '10px 0' }}>
          {TYPES.map(([k, key]) => (
            <button key={k} className={`prof-chip ${tip === k ? 'on' : ''}`}
              onClick={() => setTip(k)}>{t(key).toUpperCase()}</button>
          ))}
        </div>
        {!d ? <div className="loading">{t('common.loading')}</div> : (
          <div className="mk-scroll">
            <table>
              <thead><tr>{COLS.map(([k, key, ta]) => (
                <th key={k} className={ta === 'r' ? 'num' : ''}>
                  <button className="th-sort" onClick={sort(k)}>{key.includes('.') ? t(key) : key}{sk === k ? (dir === 1 ? ' ↑' : ' ↓') : ''}</button>
                </th>))}</tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.symbol}>
                    <td><Link to={lang === 'en' ? `/en/bond/${r.symbol.toLowerCase()}` : `/obveznica/${r.symbol.toLowerCase()}`}><b>{r.symbol}</b></Link>
                      {r.stale && <i className="mk-ill" title={t('bond.staleTitle')}> {t('mkt.illiq')}</i>}</td>
                    <td>{r.issuer || <span className="flag">{t('bond.masterInProgress')}</span>}</td>
                    <td className="basis">{btypeLabel(r.btype, t)}</td>
                    <td className="mono">{fmtDate(r.maturity_date)}</td>
                    <td className="num">{pct(r.coupon_pct, 3)}</td>
                    <td className="num">{r.price_pct !== null && r.price_pct !== undefined
                      ? `${num(r.price_pct, 2)}` : t('common.na')}
                      {r.price_date && <div className="fund-src">{fmtDate(r.price_date)}</div>}</td>
                    <td className="num">{pct(r.ytm_pct)}</td>
                    <td className="num">{r.duration ? num(r.duration.modified, 2) : t('common.na')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="disc" style={{ marginTop: 24 }}>
          {t('bond.disc')}{' '}
          <Link to={lang === 'en' ? '/en/methodology' : '/metodologija'}>{t('common.methodology')}</Link>.{' '}
          {t('common.notAdvice')}
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}

export function ObveznicaDetail() {
  const { symbol } = useParams()
  const d = useObveznice()
  const { lang, t } = useLang()
  const r = d?.rows?.find((x) => x.symbol.toLowerCase() === symbol)
  useEffect(() => {
    if (r) document.title = `${r.symbol} ${t('bond.docTitle')} · Burzovni list`
  }, [r, lang])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        {!d ? <div className="loading">{t('common.loading')}</div>
          : !r ? (
            <section><div className="mk-title"><h1>{t('bond.notFound')}</h1></div>
              <p className="imp-p"><Link to={lang === 'en' ? '/en/bonds' : '/obveznice'}>← {t('bond.allBonds')}</Link></p></section>
          ) : (
            <>
              <div className="mk-title">
                <h1>{r.symbol} — {r.issuer || t('bond.issuerInProgress')} ({btypeLabel(r.btype, t)} {t('bond.bond')})</h1>
                <span>{r.series_name || r.isin} · {t('bond.maturity')} {fmtDate(r.maturity_date)}
                  {r.stale ? ` · ${t('bond.priceIndicative')}` : ''}</span>
              </div>
              <div className="kv" style={{ marginBottom: 16 }}>
                <div className="cell"><div className="k">{t('bond.cleanPrice')}</div>
                  <div className="v">{r.price_pct !== null && r.price_pct !== undefined ? num(r.price_pct, 2) : t('common.na')}</div>
                  <div className="n">{r.price_date ? `EOD ${fmtDate(r.price_date)}` : t('bond.noTrading')}</div></div>
                <div className="cell"><div className="k">{t('bond.col.coupon')}</div>
                  <div className="v">{pct(r.coupon_pct, 3)}</div>
                  <div className="n">{t('bond.annually')}{r.freq_assumed ? ` · ${t('bond.assumption')}` : ''}</div></div>
                <div className="cell"><div className="k">YTM</div>
                  <div className="v">{pct(r.ytm_pct)}</div>
                  <div className="n">{t('bond.ytmLong')}</div></div>
                <div className="cell"><div className="k">{t('bond.currentYield')}</div>
                  <div className="v">{pct(r.current_yield_pct)}</div></div>
                <div className="cell"><div className="k">{t('bond.col.duration')}</div>
                  <div className="v">{r.duration ? num(r.duration.modified, 2) : t('common.na')}</div>
                  <div className="n">{r.duration ? `Macaulay ${num(r.duration.macaulay, 2)} g` : ''}</div></div>
                <div className="cell"><div className="k">{t('bond.accrued')}</div>
                  <div className="v">{r.accrued_pct !== null && r.accrued_pct !== undefined ? num(r.accrued_pct, 3) : t('common.na')}</div>
                  <div className="n">{t('bond.pctOfPar')} · {r.day_count}{r.day_count_assumed ? ` · ${t('bond.assumption')}` : ''}</div></div>
              </div>
              {r.series?.length > 1 && (
                <IndexChart series={r.series.map((p) => ({ date: p.date, value: p.price_pct }))}
                  label={`${r.symbol} · ${t('bond.chartLabel')}`} />
              )}
              {r.schedule?.length > 0 && (
                <section style={{ marginTop: 24 }}>
                  <div className="sec-label">{t('bond.schedule')}</div>
                  <table>
                    <thead><tr><th>{t('bond.schedDate')}</th><th className="num">{t('bond.schedAmount')}</th><th>{t('bond.schedKind')}</th></tr></thead>
                    <tbody>
                      {r.schedule.map((c) => (
                        <tr key={c.date}>
                          <td className="mono">{fmtDate(c.date)}</td>
                          <td className="num">{num(c.amount_pct, 3)}</td>
                          <td className="basis">{c.amount_pct > 90 ? t('bond.couponPrincipal') : t('bond.coupon')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="fund-src">{r.freq_assumed ? t('bond.annualFreqAssumed') : ''}{t('bond.scheduleSrc')}</p>
                </section>
              )}
              <div className="disc" style={{ marginTop: 24 }}>
                {t('bond.detDisc')}{' '}
                <Link to={lang === 'en' ? '/en/methodology' : '/metodologija'}>{t('common.methodology')}</Link>.{' '}
                {t('common.notAdvice')}
              </div>
            </>
          )}
      </main>
      <SiteFooter />
    </div>
  )
}
