import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { GapCell, SiteFooter, SiteHeader, chg, chgCol, useOverview } from './Shell.jsx'
import { TemperatureBar, useIndeksi } from './Indeksi.jsx'
import { fmtDate as fmtD, num } from './format.js'
import { useLang } from './i18n/LangContext.jsx'

const eur0 = (v) => (v === null || v === undefined ? '—' : num(v, 2))

function Movers({ title, list, nav, stockPath }) {
  return (
    <div>
      <h2 className="mk-h2">{title}</h2>
      <div className="mk-movers">
        {list.map((s) => (
          <div key={s.ticker} className="mk-mrow" onClick={() => nav(stockPath(s.company))}>
            <b>{s.ticker}</b>
            <span className="mk-nm">{s.name}</span>
            <span className="mono">{eur0(s.price)}</span>
            <span className="mono" style={{ color: chgCol(s.change_pct) }}>{chg(s.change_pct)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Stupci tablice 'Sve dionice' — svi sortabilni klikom na zaglavlje (kao Screener)
const MK_COLS = [
  ['ticker', 'mkt.col.stock', 'l'], ['price', 'mkt.col.last', 'r'], ['change_pct', 'mkt.col.change', 'r'],
  ['turnover', 'mkt.col.turnover', 'r'], ['zone', 'mkt.col.zone', 'r'], ['gap', 'mkt.col.gap', 'l'],
]

export default function Trziste() {
  const ov = useOverview()
  const idx = useIndeksi() // M-IDX: temperatura tržišta na naslovnici
  const nav = useNavigate()
  const { lang, t } = useLang()
  const stockPath = (c) => (lang === 'en'
    ? `/en/stock/${String(c).toLowerCase()}` : `/dionica/${String(c).toLowerCase()}`)
  // default: PROMET silazno (kao dosad); klik na isto zaglavlje obrće smjer
  const [sk, setSk] = useState('turnover'); const [dir, setDir] = useState(-1)
  useEffect(() => { document.title = `${t('mkt.pageTitle')} · Burzovni list` }, [lang])
  if (!ov) return <div className="wrap"><SiteHeader /><div className="loading">{t('common.loading')}</div></div>
  // zadnji trgovinski dan na tržištu (max datum EOD zapisa) — dobitnici i
  // gubitnici DANA smiju biti samo dionice stvarno trgovane TAJ dan (ustajala
  // promjena od prije nije "promjena dana")
  const latestDate = ov.stocks.reduce((m, s) => (s.date && s.date > m ? s.date : m), '')
  const dateTxt = latestDate ? fmtD(latestDate) : null
  const withChg = ov.stocks.filter((s) => s.change_pct !== null
    && s.change_pct !== undefined && s.date === latestDate)
  const gainers = [...withChg].sort((a, b) => b.change_pct - a.change_pct).slice(0, 4)
  const losers = [...withChg].sort((a, b) => a.change_pct - b.change_pct).slice(0, 4)
  // isti mehanizam kao Screener: string lokalno, null/n-p uvijek na kraj
  const gap = (s) => (s.zone_low === null || s.zone_low === undefined || !s.price ? null
    : s.price > s.zone_high ? s.price / s.zone_high - 1
      : s.price < s.zone_low ? s.price / s.zone_low - 1 : 0)
  const sortVal = (s) => (sk === 'gap' ? gap(s)
    : sk === 'zone' ? (s.zone_low === null || s.zone_low === undefined
      ? null : (s.zone_low + s.zone_high) / 2)
      : s[sk])
  const list = [...ov.stocks].sort((a, b) => {
    const av = sortVal(a); const bv = sortVal(b)
    if (typeof av === 'string' || typeof bv === 'string') return String(av).localeCompare(String(bv)) * dir
    const an = av === null || av === undefined ? Infinity * dir : av
    const bn = bv === null || bv === undefined ? Infinity * dir : bv
    return (an - bn) * dir
  })
  const sort = (k) => () => { setDir(sk === k ? -dir : k === 'ticker' ? 1 : -1); setSk(k) }
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title">
          <h1>{t('home.title')}</h1>
          {/* M32: svježina izvedena iz STVARNOG datuma exporta — ako pipeline
              jedan dan ne uspije, datum pošteno ostaje na zadnjem podatku */}
          <span>{t('mkt.subtitle')}{dateTxt ? ` ${t('mkt.subtitleFor')} ${dateTxt}` : ''} · {t('mkt.subtitleUpdate')}</span>
        </div>
        <div className="mk-idx">
          {ov.indices.length ? ov.indices.map((ix) => (
            <Link to={lang === 'en' ? '/en/indices' : '/indeksi'} className="mk-idx-c mk-idx-link" key={ix.name}
              title={t('mkt.allIndices')}>
              <div className="prof-klabel">{ix.name} →</div>
              <div className="mk-idx-v">{num(ix.value, 2)}</div>
              <div className="mono" style={{ color: chgCol(ix.change_pct), fontSize: 12 }}>{chg(ix.change_pct)}</div>
            </Link>
          )) : <div className="mk-idx-c"><div className="prof-klabel">{t('nav.indices').toUpperCase()}</div><div className="np">{t('mkt.indicesNone')}</div></div>}
          <div className="mk-idx-c">
            <div className="prof-klabel">{t('mkt.tracked')}</div>
            <div className="mk-idx-v">{ov.stocks.length}</div>
            <div className="mono" style={{ fontSize: 12, color: 'rgba(38,46,51,0.6)' }}>{t('mkt.classesInSystem')}</div>
          </div>
        </div>
        <TemperatureBar t={idx?.temperature} />
        <div className="mk-movers-grid">
          <Movers title={`${t('mkt.gainers')}${dateTxt ? ` · ${dateTxt}` : ''}`} list={gainers} nav={nav} stockPath={stockPath} />
          <Movers title={`${t('mkt.losers')}${dateTxt ? ` · ${dateTxt}` : ''}`} list={losers} nav={nav} stockPath={stockPath} />
        </div>
        <div className="subnote" style={{ marginTop: 6 }}>
          {t('mkt.moversNote1')} {dateTxt || '—'}; {t('mkt.moversNote2')}
        </div>
        <div className="mk-title2">
          <h2 className="mk-h2">{t('common.allStocks')}</h2>
          <span className="subnote" style={{ margin: 0 }}>{t('mkt.sortNote')}</span>
        </div>
        <div className="mk-scroll">
          <div className="mk-table">
            <div className="mk-hd">
              {MK_COLS.map(([k, key, ta]) => (
                <button key={k} className={ta} onClick={sort(k)}>
                  {t(key)}{sk === k ? (dir === 1 ? ' ↑' : ' ↓') : ''}
                </button>
              ))}
            </div>
            {list.map((s) => (
              <div className="mk-row" key={s.ticker} onClick={() => nav(stockPath(s.company))}>
                <span className="mk-name"><b>{s.ticker}</b><em>{s.name}</em>
                  {s.illiquid && <i className="mk-ill">{t('mkt.illiq')}</i>}</span>
                <span className="r mono">{eur0(s.price)}</span>
                <span className="r mono" style={{ color: chgCol(s.change_pct) }}>{chg(s.change_pct)}</span>
                <span className="r mono dim">{s.turnover ? num(s.turnover, 0) : '—'}</span>
                <span className="r mono pine">{s.zone_low !== null && s.zone_low !== undefined
                  ? `${num(s.zone_low, 0)}–${num(s.zone_high, 0)}` : '—'}</span>
                <GapCell s={s} />
              </div>
            ))}
            <div className="mk-legend">
              <span><i className="mk-sw-zone" />{t('mkt.legendZone')}</span>
              <span><i className="mk-sw-tick" style={{ background: '#9E2B25' }} />{t('mkt.legendPrice')}</span>
              <span><i className="mk-sw-tick" style={{ background: '#2F5D86' }} />{t('mkt.legendPref')}</span>
              <span>{t('mkt.legendIlliq')}</span>
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
