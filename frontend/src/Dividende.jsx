import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { fmtDate, num } from './format.js'
import { useLang } from './i18n/LangContext.jsx'

/* M22: agregirani dividendni kalendar (/dividende) — činjenični pregled svih
   isplata i najava iz EHO objava. MAR: bez rankinga "najboljih" prinosa —
   sortiranje je korisnikov izbor; prijedlog je vidljivo označen kao
   neizglasan. Podaci: /data/dividende.json (build_dividende.py). */

const FILTERS = [
  ['sve', 'div.f.all'], ['paid', 'div.f.paid'], ['upcoming', 'div.f.upcoming'],
  ['proposed', 'div.f.proposed'],
]

const COLS = [
  ['company', 'div.col.stock', 'l'], ['amount_eur', 'div.col.amount', 'r'],
  ['yield_now', 'div.col.yield', 'r'], ['payout_ratio', 'div.col.payout', 'r'],
  ['continuity', 'div.col.continuity', 'r'],
  ['ex_date', 'div.col.ex', 'r'], ['payment_date', 'div.col.pay', 'r'],
  ['status', 'common.status', 'l'],
]

/* v3 DIV: filter po TIPU isplate (default: sve; jednokratne su vizualno
   označene badgeom u svakom retku) */
const TYPE_FILTERS = [
  ['sve', 'div.tf.all'], ['redovna', 'div.tf.regular'],
  ['jednokratna', 'div.tf.oneoff'], ['iz_zadrzane_dobiti', 'div.tf.retained'],
]

export function TypeBadge({ type, t }) {
  if (!type || type === 'redovna') {
    return type ? <span className="div-onoff reg">{t('div.type.regular')}</span> : null
  }
  return <span className="div-onoff">
    {type === 'iz_zadrzane_dobiti' ? t('div.type.retained') : t('div.type.extraordinary')}</span>
}

/* % dobiti pripadne fiskalne godine; >100% eksplicitno; bez dobiti u bazi
   '—' s objašnjenjem (NIKAD prema krivoj godini) */
export function PayoutCell({ r, t }) {
  if (r.payout_ratio === null || r.payout_ratio === undefined) {
    return <i className="np" title={`${t('div.payoutNa')} (FY${r.fiscal_year ?? '?'})`}>—</i>
  }
  if (r.payout_ratio > 1) {
    return <span title={r.classified_reason || ''}>{t('div.payoutOver')}</span>
  }
  return <span title={r.classified_reason || ''}>{num(r.payout_ratio * 100, 0)} %</span>
}

function StatusBadge({ s, t }) {
  if (s === 'paid') return <span className="okflag">{t('div.badge.paid')}</span>
  if (s === 'proposed') {
    return <span className="flag">{t('div.badge.proposed')}</span>
  }
  return <span className="div-upcoming">{t('div.badge.upcoming')}</span>
}

function Row({ r, nav, hist, t, lang }) {
  const h = hist?.[r.company]
  const target = lang === 'en'
    ? `/en/stock/${String(r.company).toLowerCase()}`
    : `/dionica/${String(r.company).toLowerCase()}`
  return (
    <div className="mk-row div-row" onClick={() => nav(target)}>
      <span className="mk-name"><b>{r.class_ticker}</b><em>{r.name}</em></span>
      <span className="r mono">{num(r.amount_eur, 2)}</span>
      <span className="r mono">{r.yield_now === null || r.yield_now === undefined
        ? <i className="np">{t('common.na')}</i> : `${num(r.yield_now * 100, 2)} %`}</span>
      <span className="r mono" title={h ? `${t('div.histTitle')}: FY${h.coverage_from} / ${num(h.avg_amount_5y, 2)} €` : undefined}>
        {h ? `${h.paid_years_of_5}/5` : '—'}</span>
      <span className="r mono"><PayoutCell r={r} t={t} /></span>
      <span className="r mono">{fmtDate(r.ex_date)}</span>
      <span className="r mono dim">{fmtDate(r.payment_date)}</span>
      <span>
        <StatusBadge s={r.status} t={t} />
        {' '}
        <TypeBadge type={r.payout_type} t={t} />
        {' '}
        <a className="fund-src" href={r.source_url} target="_blank" rel="noreferrer"
          onClick={(e) => e.stopPropagation()}>{t('common.source')}</a>
      </span>
    </div>
  )
}

export default function Dividende() {
  const nav = useNavigate()
  const { lang, t } = useLang()
  const [data, setData] = useState(null)
  const [filter, setFilter] = useState('sve')
  const [tfilter, setTfilter] = useState('sve')
  const [sk, setSk] = useState('ex_date'); const [dir, setDir] = useState(1)
  useEffect(() => {
    fetch('/data/dividende.json').then((r) => r.json()).then(setData).catch(() => setData({ rows: [] }))
    document.title = `${t('nav.dividends')} · Burzovni list`
  }, [lang])
  const today = new Date().toISOString().slice(0, 10)

  const rows = useMemo(() => {
    if (!data) return []
    let list = data.rows.filter((r) => filter === 'sve' || r.status === filter)
    list = list.filter((r) => tfilter === 'sve' || r.payout_type === tfilter)
    const val = (r) => r[sk]
    list = [...list].sort((a, b) => {
      if (sk === 'ex_date') {
        // kronološki: što dolazi sljedeće gore — budući ex-datumi uzlazno,
        // zatim prošli silazno (jučerašnja odmah ispod nadolazećih)
        const ka = a.ex_date || '9999'; const kb = b.ex_date || '9999'
        const fa = ka >= today; const fb = kb >= today
        if (fa !== fb) return (fa ? -1 : 1) * dir
        return (fa ? ka.localeCompare(kb) : kb.localeCompare(ka)) * dir
      }
      const av = val(a); const bv = val(b)
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av ?? '').localeCompare(String(bv ?? '')) * dir
      }
      const an = av === null || av === undefined ? -Infinity * dir : av
      const bn = bv === null || bv === undefined ? -Infinity * dir : bv
      return (bn - an) * dir
    })
    return list
  }, [data, filter, tfilter, sk, dir, today])

  const soon = useMemo(() => {
    if (!data) return []
    const lim = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10)
    return data.rows.filter((r) => r.status !== 'paid' && r.ex_date
      && r.ex_date >= today && r.ex_date <= lim)
      .sort((a, b) => a.ex_date.localeCompare(b.ex_date))
  }, [data, today])

  const sort = (k) => () => { setDir(sk === k ? -dir : 1); setSk(k) }
  if (!data) return <div className="shellpg"><SiteHeader /><div className="loading">{t('common.loading')}</div></div>
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title">
          <h1>{t('div.pageTitle')}</h1>
          <span>{t('div.subtitle')} {fmtDate(data.as_of)}</span>
        </div>

        {soon.length > 0 && (
          <section className="div-soon">
            <div className="sec-label">{t('div.soon')}</div>
            <div className="mk-scroll"><div className="div-table">
              <div className="mk-hd div-hd-static">
                <span>{t('div.col.stock')}</span><span className="r">{t('div.col.amount')}</span><span className="r">{t('div.col.yield')}</span>
                <span className="r">{t('div.col.ex')}</span><span className="r">{t('div.col.pay')}</span><span>{t('common.status')}</span>
              </div>
              {soon.map((r, i) => <Row r={r} nav={nav} hist={data.history} t={t} lang={lang} key={i} />)}
            </div></div>
            <div className="subnote">{t('div.soonNote')}</div>
          </section>
        )}

        <div className="mk-title2">
          <h2 className="mk-h2">{t('div.allTitle')} ({new Date().getFullYear()})</h2>
          <div className="prof-chips">
            {FILTERS.map(([k, key]) => (
              <button key={k} className={`prof-chip ${filter === k ? 'on' : ''}`}
                onClick={() => setFilter(k)}>{t(key)}</button>
            ))}
            <span className="dim">·</span>
            {TYPE_FILTERS.map(([k, key]) => (
              <button key={k} className={`prof-chip ${tfilter === k ? 'on' : ''}`}
                onClick={() => setTfilter(k)}>{t(key)}</button>
            ))}
          </div>
        </div>
        <div className="mk-scroll">
          <div className="div-table">
            <div className="mk-hd">
              {COLS.map(([k, key, ta]) => (
                <button key={k} className={ta} onClick={sort(k)}>
                  {t(key)}{sk === k ? (dir === 1 ? ' ↑' : ' ↓') : ''}
                </button>
              ))}
            </div>
            {rows.length ? rows.map((r, i) => <Row r={r} nav={nav} hist={data.history} t={t} lang={lang} key={i} />)
              : <div className="prof-empty-box">{t('div.emptyFilter')}</div>}
            <div className="mk-legend">
              <span>{t('div.legendYield')}</span>
              <span>{t('div.legendPayout')}</span>
              <span>{t('div.legendTypes')}</span>
              <span>{t('div.legendDash')}</span>
            </div>
          </div>
        </div>
        <div className="disc">
          {lang === 'en' ? '' : data.note} {t('div.disc')}
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
