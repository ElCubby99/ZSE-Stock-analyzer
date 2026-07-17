import React, { useEffect, useState } from 'react'
import { OmfHolders } from './MirovinskiFondovi.jsx'
import { NavLink, useNavigate, useParams } from 'react-router-dom'
import { pushEvent } from './consent.jsx'
import VerdictSpread from './VerdictSpread.jsx'
import {
  AnalysisUnavailable, Dividends, IlliquidBanner, PriceChart, ProfileHeader,
  SectionRule, StatsStrip,
} from './MarketProfile.jsx'
import { AnchorPanel, FinChart, Risks, SecondaryList } from './AnalysisBlocks.jsx'
import { Legend } from './Legend.jsx'
import MethodologyNote from './MethodologyNote.jsx'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { Comparison, IndicatorGroups, KeyIndicators, NewsTab, TabBar } from './StockTabs.jsx'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'
import { sectorLabel } from './sectorLabels.mjs'
import { dash, eur, fmtDate, meur, num, pct } from './format.js'

// live firme (orchestrator) + CROS/ZABA (M1–M5) + HPB/HT (samo tržišni profil)
const TICKERS = ['ADRS', 'CROS', 'ZABA', 'ADPL', 'ARNT', 'ATGR', 'DLKV', 'HPB',
  'HT', 'IG', 'KODT', 'KOEI', 'PODR', 'RIVP', 'SPAN', 'TOK', 'ZITO']

// leće metoda za naraciju raskoraka (opis mehanike, ne preporuka) — i18n ključevi
const LENS_KEYS = {
  multiples_relative: 'sp.lens.multiples_relative',
  ddm_gordon: 'sp.lens.ddm_gordon',
  justified_pb_roe: 'sp.lens.justified_pb_roe',
  residual_income: 'sp.lens.residual_income',
  sotp_nav: 'sp.lens.sotp_nav',
  ev_ebitda: 'sp.lens.ev_ebitda',
  dcf_fcf: 'sp.lens.dcf_fcf',
}

function classCss(i) { return i === 0 ? 'ord' : 'prf' }

// M8: arhetipovi i imena metoda za naraciju sidrene fer-zone — i18n ključevi
const ARCH_KEYS = { holding: 'sp.arch.holding', capital: 'sp.arch.capital',
  operating: 'sp.arch.operating' }
const METHOD_KEYS = {
  sotp_nav: 'sp.method.sotp_nav', residual_income: 'sp.method.residual_income',
  justified_pb_roe: 'sp.method.justified_pb_roe', dcf_fcf: 'sp.method.dcf_fcf',
  multiples_relative: 'sp.method.multiples_relative', ev_ebitda: 'sp.method.ev_ebitda',
  ddm_gordon: 'sp.method.ddm_gordon',
}

/* ---------- v2 sekcije ---------- */

/* M9: mini trend prihoda i EBITDA-e (barovi iz baze) + ČINJENIČNA naracija */
function TrendBlock({ trend }) {
  const { lang, t } = useLang()
  if (!trend || !trend.series.length) return null
  const s = trend.series
  const vals = s.flatMap((r) => [r.revenue, r.ebitda]).filter((v) => v !== null)
  if (!vals.length) return null
  const vmax = Math.max(...vals)
  const W = 460; const H = 150; const pB = 22; const pT = 26
  const groupW = W / s.length
  const barW = Math.min(44, groupW / 2.6)
  const yH = (v) => (v / vmax) * (H - pT - pB)
  return (
    <section>
      <div className="sec-label">{t('sp.trendLabel1')} {tx(trend.revenue_label, lang).toLowerCase()} {t('sp.trendLabel2')}</div>
      <div className="trend-grid">
        <svg viewBox={`0 0 ${W} ${H}`} className="trend-svg" role="img"
          aria-label={t('sp.trendAria')}>
          {s.map((r, i) => {
            const cx = i * groupW + groupW / 2
            return (
              <g key={r.year}>
                {r.revenue !== null && (
                  <>
                    <rect x={cx - barW - 2} y={H - pB - yH(r.revenue)} width={barW}
                      height={yH(r.revenue)} fill="#2F5D86" opacity="0.85" />
                    <text x={cx - barW / 2 - 2} y={H - pB - yH(r.revenue) - 5}
                      textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="9.5"
                      fill="#5C6772">{num(r.revenue / 1e6, 0)}</text>
                  </>
                )}
                {r.ebitda !== null && (
                  <>
                    <rect x={cx + 2} y={H - pB - yH(r.ebitda)} width={barW}
                      height={yH(r.ebitda)} fill="#1F6E5A" opacity="0.85" />
                    <text x={cx + barW / 2 + 2} y={H - pB - yH(r.ebitda) - 5}
                      textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="9.5"
                      fill="#5C6772">{num(r.ebitda / 1e6, 0)}</text>
                  </>
                )}
                <text x={cx} y={H - 7} textAnchor="middle"
                  fontFamily="IBM Plex Mono" fontSize="10.5" fill="#5C6772">FY{r.year}</text>
              </g>
            )
          })}
        </svg>
        <div>
          <p className="trend-narr">{tx(trend.narration, lang)}</p>
          <div className="legend">
            <span><i className="swatch" style={{ background: '#2F5D86' }} /> {tx(trend.revenue_label, lang)} (M€)</span>
            <span><i className="swatch" style={{ background: '#1F6E5A' }} /> EBITDA (M€)</span>
          </div>
        </div>
      </div>
      <div className="subnote">{tx(trend.note, lang)}.</div>
    </section>
  )
}

/* M9: profil poslovanja — SAMO činjenice iz izvješća; epiteti = tvrdnje
   izdavatelja, označene i citirane. Bez izvora -> sekcija kaže "nema u bazi".
   Slobodni per-firma tekstovi (activity, segmenti, tvrdnje) prikazuju se
   kako jesu; u EN nose diskretnu oznaku da je izvorni tekst hrvatski. */
function BusinessProfile({ bp }) {
  const { lang, t } = useLang()
  const srcHr = lang === 'en' && <span className="fund-src"> {t('sp.hrSourceNote')}</span>
  return (
    <section>
      <div className="sec-label">
        {bp?.generic ? t('sp.bpTitle') : t('sp.bpTitleFromReport')}
        {bp?.generic && <span className="flag" style={{ marginLeft: 8 }}>{t('sp.bpGeneric')}</span>}
      </div>
      {!bp ? (
        <div className="subnote"><span className="flag">{t('mkt.indicesNone')}</span>{' '}
          {t('sp.bpNone')}</div>
      ) : bp.generic ? (
        <>
          <p className="bp-activity">{bp.activity}{srcHr}</p>
          <div className="subnote">{tx(bp.note, lang)}.</div>
        </>
      ) : (
        <>
          <p className="bp-activity">{bp.activity}
            {bp.activity_source_page && <span className="fund-src"> ({bp.activity_source_page})</span>}
            {srcHr}
          </p>
          <div className="bp-grid">
            {bp.segments.length > 0 && (
              <div>
                <div className="bp-h">{t('sp.bpSegments')}{srcHr}</div>
                <ul className="bp-list">
                  {bp.segments.map((sg) => (
                    <li key={sg.name}>
                      <b>{sg.name}</b>{sg.description ? ` — ${sg.description}` : ''}
                      {sg.source_page && <span className="fund-src"> ({sg.source_page})</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div>
              {bp.markets.length > 0 && (
                <>
                  <div className="bp-h">{t('sp.bpMarkets')}{srcHr}</div>
                  <ul className="bp-list">
                    {bp.markets.map((m) => (
                      <li key={m.market}>{m.market}
                        {m.source_page && <span className="fund-src"> ({m.source_page})</span>}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <div className="bp-h">{t('sp.bpExport')}</div>
              {bp.export_share ? (
                <p className="bp-export">
                  <b>{num(bp.export_share.value * 100, 0)}%</b> — {tx(bp.export_share.basis, lang)}
                  {bp.export_share.source_page && <span className="fund-src"> ({bp.export_share.source_page})</span>}
                </p>
              ) : (
                <p className="bp-export"><span className="np">{t('sp.bpExportNa')}</span></p>
              )}
            </div>
          </div>
          {bp.issuer_claims.length > 0 && (
            <div className="bp-claims">
              <div className="bp-h">{t('sp.bpClaims')}{srcHr}</div>
              <ul className="bp-list">
                {bp.issuer_claims.map((c, i) => (
                  <li key={i}>
                    <span className="flag">{t('sp.bpClaimFlag')}</span> {c.claim}
                    {c.source_page && <span className="fund-src"> ({c.source_page})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="subnote">{tx(bp.note, lang)}. {t('common.source')}: {tx(bp.source, lang)}.</div>
        </>
      )}
    </section>
  )
}

function Fin3Y({ f3 }) {
  const { lang, t } = useLang()
  if (!f3 || !f3.years.length) return null
  const fmtVal = (r, y) => {
    const v = r.values[String(y)]
    if (v === null || v === undefined) return <span className="flag">{t('mkt.indicesNone')}</span>
    return r.unit === 'eur_per_share' ? eur(v) : meur(v)
  }
  const pctCell = (v) => {
    if (v === null || v === undefined) return <td className="num">{dash}</td>
    return <td className={`num ${v >= 0 ? 'pos' : 'neg'}`}>{v >= 0 ? '+' : ''}{num(v * 100, 1)}%</td>
  }
  return (
    <section>
      <div className="sec-label">{t('sp.finTitle1')} {f3.years.length} {t('sp.finTitle2')}</div>
      <table>
        <thead>
          <tr>
            <th>{t('fin.item')}</th>
            {f3.years.map((y) => <th className="num" key={y}>FY{y}</th>)}
            <th className="num">YoY</th><th className="num">CAGR</th>
          </tr>
        </thead>
        <tbody>
          {f3.rows.map((r) => (
            <tr key={r.item}>
              <td>{tx(r.label, lang)}</td>
              {f3.years.map((y) => <td className="num" key={y}>{fmtVal(r, y)}</td>)}
              {pctCell(r.yoy_pct)}
              {pctCell(r.cagr_pct)}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="subnote">{tx(f3.note, lang)}. {t('sp.finYoyNote')}</div>
    </section>
  )
}

function Balance({ b }) {
  const { lang, t } = useLang()
  if (!b) return null
  const lev = b.leverage
  return (
    <section>
      <div className="sec-label">{t('sp.balTitle')}{b.fiscal_year}</div>
      <div className="kv">
        <div className="cell"><div className="k">{t('li.total_assets')}</div><div className="v">{meur(b.total_assets, 0)}</div></div>
        <div className="cell"><div className="k">{t('sp.balEquityParent')}</div><div className="v">{meur(b.equity_parent, 0)}</div></div>
        <div className="cell"><div className="k">{t('sp.balBvps')}</div><div className="v">{eur(b.bvps)}</div></div>
        {b.is_financial ? (
          <div className="cell">
            <div className="k">{t('sp.balNetDebtEbitda')}</div>
            <div className="v np">{t('common.na')}</div>
          </div>
        ) : (
          <>
            <div className="cell">
              <div className="k">{t('sp.balNetDebt')}</div>
              <div className="v">{lev && lev.net_debt !== null ? meur(lev.net_debt, 0) : dash}</div>
              <div className="n">{tx(lev?.components_note, lang)}</div>
            </div>
            <div className="cell">
              <div className="k">{t('sp.balNetDebtEbitda')}</div>
              <div className="v">{lev && lev.net_debt_to_ebitda !== null ? `${num(lev.net_debt_to_ebitda, 2)}×` : dash}</div>
            </div>
          </>
        )}
      </div>
      {b.leverage_note && <div className="subnote">{tx(b.leverage_note, lang)}</div>}
      {!b.is_financial && lev?.current_ratio === null && (
        <div className="subnote">{tx(lev.current_ratio_note, lang)}.</div>
      )}
    </section>
  )
}

function Segments({ seg }) {
  const { lang, t } = useLang()
  if (!seg) return null
  const rec = seg.reconciliation
  return (
    <section>
      <div className="sec-label">{t('sp.segTitle')}{seg.fiscal_year}</div>
      <table>
        <thead>
          <tr><th>{t('sp.colSegment')}</th><th className="num">{t('sp.colRevenue')}</th><th className="num">EBITDA</th>
            <th className="num">{t('sp.colEbitdaMargin')}</th><th className="num">{t('sp.colNet')}</th></tr>
        </thead>
        <tbody>
          {seg.rows.map((r) => (
            <tr key={r.key}>
              <td>{tx(r.label, lang)} <span className="fund-src">{r.source_page ? '' : ''}</span></td>
              <td className="num">{meur(r.revenue, 0)}</td>
              <td className="num">{r.ebitda === null ? <span className="np">{t('common.na')}</span> : meur(r.ebitda, 1)}</td>
              <td className="num">{r.ebitda_margin === null ? dash : pct(r.ebitda_margin)}</td>
              <td className="num">{meur(r.net_result, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rec && (
        <div className="subnote">
          {rec.revenue_comparable ? (
            <>{t('sp.segSum1')} {meur(rec.revenue_sum, 0)} {t('sp.segSum2')} {meur(rec.group_revenue, 0)}
              {rec.revenue_residual !== null && <> {t('sp.segSum3')} {meur(rec.revenue_residual, 0)} {t('sp.segSum4')}</>}. </>
          ) : (
            <>{t('sp.segRecNa')} <span className="np">{tx(rec.revenue_note, lang)}</span>. </>
          )}
          {tx(rec.note, lang)}.
        </div>
      )}
    </section>
  )
}

function BankKpi({ bk }) {
  const { lang, t } = useLang()
  if (!bk) return null
  return (
    <section>
      <div className="sec-label">{t('sp.bankTitle')}{bk.fiscal_year}</div>
      <div className="kv">
        {bk.kpis.map((k) => (
          <div className="cell" key={k.key}>
            <div className="k">{tx(k.label, lang)}</div>
            <div className="v">
              {k.missing ? <span className="flag">{t('mkt.indicesNone')}</span> : pct(k.value, 2)}
            </div>
            <div className="n">{tx(k.basis, lang)}</div>
          </div>
        ))}
      </div>
      <div className="subnote">{tx(bk.note, lang)}.</div>
    </section>
  )
}

function ChangeCell({ r, hasPrev }) {
  const { t } = useLang()
  if (!hasPrev) return <span>{dash}</span>
  if (r.entered) return <span className="okflag">{t('sp.enteredTop10')}</span>
  if (r.change_pp === null || r.change_pp === undefined) return <span>{dash}</span>
  const v = r.change_pp
  const sign = v > 0 ? '+' : v < 0 ? '−' : '±'
  const col = v > 0 ? '#1F6E5A' : v < 0 ? '#9E2B25' : 'rgba(38,46,51,0.55)'
  return <span style={{ color: col }}>{sign}{num(Math.abs(v), 2)} {t('sp.pp')}</span>
}

function Top10({ t10 }) {
  const { lang, t } = useLang()
  if (!t10) return null
  const hasPrev = !!t10.prev_snapshot_date
  return (
    <section>
      <div className="sec-label">{t('sp.top10Title')}</div>
      <div className="subnote" style={{ marginBottom: 8 }}>
        {t('sp.snapshot')} {fmtDate(t10.snapshot_date)} — {tx(t10.source_label, lang)}.
        {hasPrev
          ? <> {t('sp.changesVs')} {fmtDate(t10.prev_snapshot_date)} ({tx(t10.prev_source_label, lang)}).</>
          : <> {tx(t10.note, lang)}.</>}
      </div>
      <table>
        <thead>
          <tr>
            <th>#</th><th>{t('sp.holderCol')}</th>
            <th className="num">{t('fund.share')}</th>
            <th className="num">{t('sp.colChange')}{hasPrev ? ` (${t('sp.pp')})` : ''}</th>
            <th>{t('common.source')}</th>
          </tr>
        </thead>
        <tbody>
          {t10.rows.map((r) => (
            <tr key={r.rank}>
              <td>{r.rank}.</td>
              <td>
                {r.name}
                {r.is_custody && <> <span className="ph">{t('sp.custodyAccount')}</span></>}
                {r.prev_name && (
                  <div className="fund-src">{t('sp.comparedWith')} {r.prev_name}</div>
                )}
              </td>
              <td className="num">{num(r.pct, 2)} %</td>
              <td className="num"><ChangeCell r={r} hasPrev={hasPrev} /></td>
              <td className="fund-src">{tx(r.source_detail, lang)}</td>
            </tr>
          ))}
          {t10.free_float_from_top10_pct !== null && t10.free_float_from_top10_pct !== undefined && (
            <tr className="sotp-total">
              <td /><td>{t('sp.ffApprox')}</td>
              <td className="num">{num(t10.free_float_from_top10_pct, 2)} %</td>
              <td /><td />
            </tr>
          )}
        </tbody>
      </table>
      {hasPrev && !!(t10.left || []).length && (
        <div className="subnote">
          {t('sp.leftTop10a')} {fmtDate(t10.prev_snapshot_date)}: {t10.left.join(' · ')}.
        </div>
      )}
      <div className="subnote">
        {tx(t10.custody_note, lang)}. {t('sp.namesAsPublished')}
      </div>
    </section>
  )
}

function Ownership({ own, liquidity }) {
  const { lang, t } = useLang()
  if (!own) return null
  const anyFlag = (liquidity?.classes || []).some((c) => c.flag !== 'ok')
  return (
    <>
    <Top10 t10={own.top10} />
    <section>
      <div className="sec-label">{t('sp.ownTitle')}</div>
      {own.holders.length ? (
        <>
          <table>
            <thead><tr><th>{t('sp.holder')}</th><th className="num">{t('fund.share')}</th><th>{t('common.source')}</th></tr></thead>
            <tbody>
              {own.holders.map((h) => (
                <tr key={h.name}>
                  <td>{h.name}{h.ticker ? ` (${h.ticker})` : ''}</td>
                  <td className="num">{pct(h.pct, 2)}</td>
                  <td className="fund-src">{tx(h.source, lang)}</td>
                </tr>
              ))}
              <tr className="sotp-total">
                <td>{t('sp.ffRow')}</td>
                <td className="num">{pct(own.free_float_pct_approx, 1)}</td>
                <td />
              </tr>
            </tbody>
          </table>
          <div className="subnote">
            {tx(own.note, lang)}.
            {own.liquidity_link && anyFlag && <> <b>{tx(own.liquidity_link, lang)}.</b></>}
          </div>
        </>
      ) : own.top10 ? (
        <div className="subnote">
          {t('sp.ownNoGraph')}
        </div>
      ) : (
        <div className="subnote"><span className="flag">{t('mkt.indicesNone')}</span> {tx(own.note, lang)}.</div>
      )}
    </section>
    </>
  )
}

function Split({ perClass, field, fmt }) {
  const vals = perClass.filter((r) => r[field] !== null && r[field] !== undefined)
  if (!vals.length) return <span>{dash}</span>
  return (
    <>
      {vals.map((r, i) => (
        <React.Fragment key={r.class_ticker}>
          {i > 0 && ' · '}
          <b className={classCss(i)}>{fmt(r[field])}</b>
        </React.Fragment>
      ))}
    </>
  )
}

function Metrics({ data }) {
  const { lang, t } = useLang()
  const m = data.metrics
  return (
    <div className="metrics">
      <div className="metric">
        <div className="k">{t('sp.epsLabel')}</div>
        <div className="v">{eur(m.eps)}</div>
        <div className="split">FY{data.fiscal_year || dash}</div>
      </div>
      <div className="metric">
        <div className="k">P/E</div><div className="v">{dash}</div>
        <div className="split"><Split perClass={m.per_class} field="pe" fmt={(v) => num(v, 1)} /></div>
      </div>
      <div className="metric">
        <div className="k">P/B</div><div className="v">{dash}</div>
        <div className="split"><Split perClass={m.per_class} field="pb" fmt={(v) => num(v, 2)} /></div>
      </div>
      <div className="metric">
        <div className="k">{t('ki.divYield')}</div><div className="v">{dash}</div>
        <div className="split"><Split perClass={m.per_class} field="div_yield" fmt={(v) => pct(v, 2)} /></div>
        {m.dps_label && <div className="split">{tx(m.dps_label, lang)}</div>}
      </div>
      <div className="metric">
        <div className="k">{t('sp.mcapShort')}</div>
        <div className="v">{m.market_cap_eur ? `${num(m.market_cap_eur / 1e6, 0)} M€` : dash}</div>
        <div className="split">{data.share_classes.length > 1 ? t('sp.allClasses') : t('sp.oneClass')}</div>
      </div>
      <div className="metric">
        <div className="k">EBITDA</div>
        <div className="v">{m.ebitda_eur ? `${num(m.ebitda_eur / 1e6, 0)} M€` : dash}</div>
        <div className="split">ROE {pct(m.roe)}</div>
      </div>
    </div>
  )
}

/* Raskorak prinosne i knjigovodstvene vrijednosti (LPLH-tip) — generirani
   komentar iz brojki OVE firme koji objašnjava naš stav kad je fer-zona
   bitno ispod/iznad knjige. Činjenice bez preporuke; zaključak čitateljev. */
function ValueVsBook({ note }) {
  const { lang, t } = useLang()
  if (!note) return null
  return (
    <section>
      <div className="sec-label">{t('sp.vvbTitle')}</div>
      <div className="controls">
        <div className="ctrl">
          <div className="top">
            <span className="name">
              {tx(note.title, lang)}{' '}
              <span className="okflag">{t('sp.sourceFlag')}</span>
            </span>
            <span className="out mono">
              BVPS {num(note.bvps, 2)} € · ROE {num(note.roe * 100, 1)} % · r {num(note.r * 100, 1)} %
            </span>
          </div>
          <div className="plain">{tx(note.plain, lang)}</div>
        </div>
      </div>
    </section>
  )
}

/* v3 A (Borisov zahtjev): test održive dividende — for-dummies raspis s
   brojkama OVE dionice, kod svake dionice gdje je test primjenjiv.
   Struktura: što je D_sust -> što je donji rub -> što je implicirani
   prinos -> koji je prag i zašto (Gordonova logika) -> verdikt. */
function DividendSanity({ rec }) {
  const { lang, t } = useLang()
  const ds = rec?.dividend_sanity
  if (!ds) return null
  // 'prolazi' je HR podatkovna konstanta (verdict iz exporta)
  const ok = ds.verdict === 'prolazi'
  return (
    <section>
      <div className="sec-label">{t('sp.dsTitle')}</div>
      <div className="controls">
        <div className="ctrl">
          <div className="top">
            <span className="name">{t('sp.dsName1')}</span>
            <span className="out mono">{num(ds.d_sust_ps, 2)} €</span>
          </div>
          <div className="plain">
            {t('sp.dsPlain1')} <b>{t('sp.dsPlain1b')}</b> {t('sp.dsPlain1c')}
          </div>
        </div>
        <div className="ctrl">
          <div className="top">
            <span className="name">{t('sp.dsName2')}</span>
            <span className="out mono">{num(ds.implied_yield_low * 100, 1)} %</span>
          </div>
          <div className="plain">
            {t('sp.dsPlain2a')} ({num(ds.zone_low, 2)} €). {t('sp.dsPlain2b')} {num(ds.d_sust_ps, 2)} € /
            {' '}{num(ds.zone_low, 2)} € = <b>{num(ds.implied_yield_low * 100, 1)} %</b> {t('sp.dsPlain2c')}
          </div>
        </div>
        <div className="ctrl">
          <div className="top">
            <span className="name">{t('sp.dsName3')}</span>
            <span className="out mono">{num(ds.threshold * 100, 1)} %</span>
          </div>
          <div className="plain">
            {t('sp.dsPlain3a')} {num(ds.r * 100, 2)} % {t('sp.dsMinus')} {tx(ds.g_source, lang)}
            {' '}= <b>{num(ds.threshold * 100, 1)} %</b>.
          </div>
        </div>
        <div className="ctrl">
          <div className="top">
            <span className="name">{t('sp.dsName4')}</span>
            <span className="out">{ds.verdict === 'prolazi (uz dividendni pod)'
              ? <span className="okflag">{t('sp.dsPassFloor')}</span>
              : ok ? <span className="okflag">{t('sp.dsPass')}</span>
                : <span className="flag">{tx(ds.verdict, lang).toUpperCase()}</span>}</span>
          </div>
          <div className="plain">
            {ds.verdict === 'prolazi (uz dividendni pod)' && ds.dividend_floor
              ? `${t('sp.dsFloor1')} ${num(ds.d_sust_ps, 2)} € ${t('sp.dsFloor2')} ${num(ds.dividend_floor.v_div, 2)} € ${t('sp.dsFloor3')}`
              : ok
                ? `${t('sp.dsOk1')} ${num(ds.implied_yield_low * 100, 1)} % ${t('sp.dsOk2')}${num(ds.threshold * 100, 1)} %${t('sp.dsOk3')}`
                : t('sp.dsElse')}
            {' '}{t('sp.dsTrail')}
          </div>
        </div>
      </div>
    </section>
  )
}

/* v3 P.1: reverse-DCF okvir — činjenična implikacija tržišne cijene,
   standardizirano za |raskorak| > 30% (umjesto alarmantnog postotka). */
function MarketImplied({ rec }) {
  const { lang, t } = useLang()
  const mi = rec?.market_implied
  if (!mi) return null
  return (
    <section>
      <div className="sec-label">{t('sp.miTitle')}</div>
      <div className="ctrl">
        <div className="top">
          <span className="name">{t('sp.miName')}</span>
          <span className="out mono">
            {mi.implied_g_pct !== null && mi.implied_g_pct !== undefined
              ? `${t('sp.miGrowth')}${num(mi.implied_g_pct, 1)} ${t('sp.miPerYear')}` : ''}
            {mi.implied_g_pct !== null && mi.implied_g_pct !== undefined
              && mi.implied_r_pct !== null && mi.implied_r_pct !== undefined ? ' · ' : ''}
            {mi.implied_r_pct !== null && mi.implied_r_pct !== undefined
              ? `r ~${num(mi.implied_r_pct, 1)} %` : ''}
          </span>
        </div>
        <div className="plain">
          {mi.implied_g_note ? `${tx(mi.implied_g_note, lang)}. ` : ''}
          {mi.implied_r_note ? `${tx(mi.implied_r_note, lang)}. ` : ''}
          {t('sp.miPlain')}
        </div>
        <details className="src-details">
          <summary>{t('sp.miFull')}</summary>
          <div className="src">{tx(mi.narrative, lang)}</div>
        </details>
      </div>
    </section>
  )
}

function Assumptions({ valuation }) {
  const { lang, t } = useLang()
  const p = valuation.params
  /* dvorazinski princip: jedna rečenica OBIČNIM jezikom vidljiva,
     tehnički izvod (CAPM, izvori, citati) iza klika — izračun se ne mijenja */
  /* v3 FAZA K: puni raspis r-a — rf + β×ERP + CRP + nelikvidnost = r,
     svaka komponenta zasebna kartica s izvorom iza klika */
  const hasStack = p.rf !== null && p.rf !== undefined && p.crp !== null && p.crp !== undefined
  const rFormula = hasStack
    ? `${num(p.rf * 100, 2)} % + ${num(p.beta, 2)} × ${num(p.erp * 100, 2)} %`
      + ` + ${num(p.crp * 100, 1)} ${t('sp.bp')}`
      + (p.illiq_premium ? ` + ${num(p.illiq_premium * 100, 1)} ${t('sp.bp')}` : '')
      + ` = ${pct(p.r, 2)}`
    : null
  const cards = [
    {
      name: t('sp.aName.r'), out: pct(p.r, 2), src: p.sources.r, sure: p.rates_calibrated,
      plain: `${t('sp.aRPlain1')} ${pct(p.r, 2)} ${t('sp.aRPlain2')}`
        + (rFormula ? ` ${t('sp.aRBreak')}${p.illiq_premium ? t('sp.aRIlliq') : ''} = ${rFormula}.` : ''),
    },
  ]
  if (hasStack) {
    cards.push({
      name: t('sp.aName.rf'), out: pct(p.rf, 2), src: p.sources.rf || p.sources.r, sure: false,
      plain: t('sp.aRfPlain'),
    })
    cards.push({
      name: t('sp.aName.erp'), out: pct(p.erp, 2), src: p.sources.erp || p.sources.r, sure: false,
      plain: t('sp.aErpPlain'),
    })
    cards.push({
      name: t('sp.aName.crp'), out: `+${num(p.crp * 100, 1)} ${t('sp.bp')}`, src: p.sources.crp || p.sources.r, sure: false,
      plain: t('sp.aCrpPlain'),
    })
  }
  cards.push({
    name: t('sp.aName.g'), src: p.sources.g, sure: p.rates_calibrated,
    out: p.g_terminal ? `${pct(p.g, 1)} · ${pct(p.g_terminal, 1)}` : pct(p.g, 1),
    plain: `${t('sp.aGPlain1')}${pct(p.g, 1)} ${t('sp.aGPlain2')} ${p.g_terminal ? pct(p.g_terminal, 1) : dash} ${t('sp.aGPlain3')}`,
  })
  if (p.growth && p.growth.g1 !== null && p.growth.g1 !== undefined) {
    /* v3.1 DIO 2: kompozitni g1 — raspis tri signala + pobjednik + badgevi */
    const gr = p.growth
    const sg = gr.signals || {}
    const sigTxt = [
      sg.g_obs !== null && sg.g_obs !== undefined
        ? `${t('sp.aSigSeries')} ${pct(sg.g_obs, 1)}`
        : `${t('sp.aSigNoSeries')}${gr.ttm_context !== null && gr.ttm_context !== undefined ? ` ${t('sp.aSigTtm1')} ${pct(gr.ttm_context, 1)} ${t('sp.aSigTtm2')}` : ''}`,
      sg.g_sust !== null && sg.g_sust !== undefined
        ? `${t('sp.aSigSust')} ${pct(sg.g_sust, 1)}`
        : null,
      sg.g_terminal !== null && sg.g_terminal !== undefined
        ? `${t('sp.aSigTerm')} ${pct(sg.g_terminal, 1)}`
        : null,
    ].filter(Boolean).join(' · ')
    cards.push({
      name: t('sp.aName.g1'),
      out: pct(gr.g1, 1),
      src: gr.source,
      sure: true,
      badge: gr.origin ? tx(gr.origin, lang) : null,
      plain: `${t('sp.aG1Plain1')} ${sigTxt}. ${t('sp.aG1Plain2')} "${tx(gr.origin, lang)}".`
        + (gr.badges && gr.badges.length ? ` ${t('sp.aG1Limits')} ${gr.badges.map((b) => tx(b, lang)).join('; ')}.` : '')
        + ` ${t('sp.aG1Plain3')}`,
    })
  }
  if (p.beta !== null && p.beta !== undefined) {
    cards.push({
      name: t('sp.aName.beta'), out: num(p.beta, 2), src: p.sources.r, sure: p.beta_calibrated,
      badge: p.beta_origin ? tx(p.beta_origin, lang) : null, // Z1: regresija / sektorska / clamp
      plain: `Beta ${num(p.beta, 2)} ${t('sp.aBetaPlain')}`,
    })
  }
  if (p.illiq_premium) {
    cards.push({
      name: t('sp.aName.illiq'), out: `+${num(p.illiq_premium * 100, 1)} ${t('sp.bp')}`,
      src: p.illiq_src || p.sources.r, sure: true,
      plain: t('sp.aIlliqPlain'),
    })
  }
  if (valuation.sotp) {
    /* v2 §4: prikaži STVARNO primijenjeni diskont s razlogom iz taksonomije;
       usporedbe idu nad HR podatkovnim konstantama iz exporta */
    const reason = p.holding_discount_reason || ''
    const operating = reason.includes('integrirani operativni parent')
    const measured = reason.includes('IZMJERENI')
    cards.push({
      name: t('sp.aName.hd'),
      out: `${num(p.holding_discount_low * 100, 0)}–${num(p.holding_discount_high * 100, 0)}%`,
      src: reason || p.sources.holding_discount,
      sure: operating || measured,
      plain: operating
        ? t('sp.aHdOper')
        : measured
          ? t('sp.aHdMeasured')
          : t('sp.aHdDefault'),
    })
  }
  cards.push({
    name: p.peers_narrow ? t('sp.aName.peersNarrow') : t('sp.aName.peers'),
    out: `${num(p.peer_pe, 2)} · ${num(p.peer_pb, 2)}`,
    src: p.sources.peers, sure: p.peers_calibrated && !p.peers_narrow,
    plain: p.peers_narrow ? t('sp.aPeersNarrowPlain') : t('sp.aPeersPlain'),
  })
  return (
    <section>
      <div className="sec-label">{t('sp.aTitle')}</div>
      <div className="controls">
        {cards.map((c) => (
          <div className="ctrl" key={c.name}>
            <div className="top">
              <span className="name">
                {c.name}{' '}
                {c.sure ? <span className="okflag">{t('sp.sourceFlag')}</span> : <span className="flag">{t('sp.assumptionFlag')}</span>}
                {c.badge && <span className="beta-badge">{c.badge}</span>}
              </span>
              <span className="out mono">{c.out}</span>
            </div>
            <div className="plain">{c.plain}</div>
            <details className="src-details">
              <summary>{t('sp.techSource')}</summary>
              <div className="src">{c.src ? tx(c.src, lang) : t('sp.noSource')}</div>
            </details>
          </div>
        ))}
      </div>
      <ul className="flaglist">
        {valuation.assumption_flags.map((f) => (
          <li key={f.key}>
            {f.status === 'izvor'
              ? <span className="okflag">{t('sp.sourceFlag')}</span>
              : <span className="flag">{t('sp.assumptionFlag')}</span>} {tx(f.label, lang)} — {tx(f.why, lang)}
          </li>
        ))}
      </ul>
    </section>
  )
}

/* v2 §7: objašnjenje klasa — prava, zašto se cijene razlikuju; fer je
   klasno-agnostičan pa se premija redovne prikazuje, ne ugrađuje */
function ClassExplainer({ data }) {
  const { lang, t } = useLang()
  const ex = data.share_class_explainer
  if (!ex) return null
  const methodHref = lang === 'en' ? '/en/methodology' : '/metodologija'
  return (
    <section>
      <div className="sec-label">{t('sp.ceTitle')}</div>
      <table>
        <thead><tr><th>{t('ki.class')}</th><th>{t('sp.colTip')}</th><th>{t('sp.colRights')}</th></tr></thead>
        <tbody>
          {ex.rows.map((r) => (
            <tr key={r.ticker}>
              <td><b>{r.ticker}</b></td>
              <td>{tx(r.type, lang)}</td>
              <td>{tx(r.rights, lang)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {(() => {
        const m = data.valuation?.reconciliation?.class_zones?._meta
        if (!m) return null
        /* 'tržišni medijan' je HR podatkovna konstanta (ratio_basis) */
        return (
          <div className="subnote">
            {t('sp.cePrem1')}{m.ordinary}{t('sp.cePrem2')}{m.preferred}):{' '}
            <b>{m.premium_pct > 0 ? '+' : ''}{num(m.premium_pct, 1)} %</b>{' '}
            ({m.ratio_basis === 'tr\u017ei\u0161ni medijan'
              ? `${t('sp.ceHist1')} ${m.ratio_n_days} ${t('sp.ceHist2')}`
              : t('sp.ceTheor')})
            {' '}{t('sp.ceTail')} <a href={methodHref}>{t('common.methodology')}</a>.
          </div>
        )
      })()}
      <div className="subnote">{tx(ex.note, lang)}</div>
    </section>
  )
}

function Narrative({ data }) {
  const { lang, t } = useLang()
  const rec = data.valuation.reconciliation
  const ran = data.valuation.ran.filter((m) => !m.no_value)
  if (!rec || ran.length < 2) {
    return <p>{t('sp.nrTooFew')}</p>
  }
  const lensTxt = (k) => (LENS_KEYS[k] ? t(LENS_KEYS[k]) : '')
  const methodName = (k) => (METHOD_KEYS[k] ? t(METHOD_KEYS[k]) : k)
  const byBase = [...ran].sort((a, b) => a.base - b.base)
  const lo = byBase[0]; const hi = byBase[byBase.length - 1]
  const sotp = ran.find((m) => m.key === 'sotp_nav')
  return (
    <>
      <p>
        {t('sp.nrLow')} <b>{tx(lo.label, lang)}</b> ({eur(lo.base, 0)}) — {lensTxt(lo.key)}.
        {' '}{t('sp.nrHigh')} <b>{tx(hi.label, lang)}</b> ({eur(hi.base, 0)}) — {lensTxt(hi.key)}.
      </p>
      {sotp && data.is_group && sotp.key !== lo.key && (
        <p className="pull">
          {t('sp.nrSotp')}
        </p>
      )}
      <p>
        {t('sp.nrZone1')} <b>{t('sp.nrZone2')}</b> ({ARCH_KEYS[rec.archetype] ? t(ARCH_KEYS[rec.archetype]) : rec.archetype}
        {rec.anchor_methods?.length ? `: ${rec.anchor_methods.map((k) => methodName(k)).join(', ')}` : ''}):{' '}
        {eur(rec.zone_low, 0)}–{eur(rec.zone_high, 0)} {t('sp.nrPerShare')}
        ({t('vs.dispersion')} {num(rec.dispersion * 100, 0)}%).
        {rec.zone_note ? ` ${tx(rec.zone_note, lang)}.` : ''}
      </p>
      {(() => {
        const secOut = ran.filter((m) => {
          const role = rec.method_roles?.[m.key]
          return role?.role === 'secondary' && role.vs_zone_pct
        })
        if (!secOut.length) return null
        const note = rec.method_roles[secOut[0].key]?.note
        return (
          <p>
            {t('sp.nrSec')}{' '}
            {secOut.map((m, i) => (
              <React.Fragment key={m.key}>
                {i > 0 && ', '}
                {tx(m.label, lang)} ({num(rec.method_roles[m.key].vs_zone_pct * 100, 0)}%)
              </React.Fragment>
            ))}
            {note ? ` — ${tx(note, lang)}.` : '.'}
            {' '}{t('sp.nrAllRange')} {eur(rec.all_methods_low, 0)}–{eur(rec.all_methods_high, 0)}.
          </p>
        )
      })()}
      <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
        {t('sp.nrWhich')}
      </p>
    </>
  )
}

/* basis vrijednosti u exportu su podatkovne konstante (dio i na HR) —
   'izvještaj' je zapisan escapeom zbog i18n linta */
const IDENTITY_BASIS_KEYS = {
  our_estimate: 'sp.basis.our_estimate', market_fallback: 'sp.basis.market_fallback',
  multiple: 'sp.basis.multiple', 'izvje\u0161taj': 'sp.basis.izvjestaj',
}

function SotpTable({ sotp }) {
  const { lang, t } = useLang()
  if (!sotp) return null
  if (sotp.identity) {
    // v2 §5: reconciliation identitet — svaka stavka s osnovom, per-share
    return (
      <section>
        <div className="sec-label">{t('sp.sotpIdTitle')}</div>
        <table>
          <thead><tr><th>{t('fin.item')}</th><th className="num">M€</th>
            <th className="num">{t('sp.colEurShare')}</th><th>{t('sp.colBasis')}</th></tr></thead>
          <tbody>
            {sotp.identity.map((row, i) => (
              <tr key={i}>
                <td>{tx(row.item, lang)}</td>
                <td className="num">{meur(row.eur)}</td>
                <td className="num">{row.per_share === null || row.per_share === undefined
                  ? dash : num(row.per_share, 2)}</td>
                <td><span className="basis">{IDENTITY_BASIS_KEYS[row.basis]
                  ? t(IDENTITY_BASIS_KEYS[row.basis]) : tx(row.basis, lang)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="subnote">
          {tx(sotp.identity_note, lang)}. {sotp.missing ? `${t('sp.outsideNav')} ${sotp.missing.map((x) => tx(x, lang)).join('; ')}.` : ''}
          {sotp.parent_child_mismatch
            ? <span className="flag" style={{ marginLeft: 6 }}>MISMATCH: {tx(sotp.parent_child_mismatch, lang)}</span>
            : null}
        </div>
      </section>
    )
  }
  return (
    <section>
      <div className="sec-label">{t('sp.sotpPartsTitle')}</div>
      <table>
        <tbody>
          {sotp.parts.map((part) => (
            <tr key={part.name}>
              <td>
                {part.name}{' '}
                {part.placeholder ? <span className="ph">{t('sp.assumpShort')}</span> : null}
              </td>
              <td className="num">{meur(part.value_eur)}</td>
            </tr>
          ))}
          {sotp.net_cash && (
            <tr>
              <td>{t('sp.netCash')} <span className="basis">({tx(sotp.net_cash.basis, lang)})</span></td>
              <td className="num">{meur(sotp.net_cash.value_eur)}</td>
            </tr>
          )}
          <tr className="sotp-total">
            <td>{t('sp.navTotal')}</td>
            <td className="num">{meur(sotp.nav_total_eur)}</td>
          </tr>
        </tbody>
      </table>
      <div className="srcnote">
        {t('sp.discount')} {sotp.holding_discount_range
          ? `${num(sotp.holding_discount_range[0] * 100, 0)}–${num(sotp.holding_discount_range[1] * 100, 0)}%`
          : dash} — {tx(sotp.holding_discount_reason, lang)}
        {sotp.market_check && (
          <> {t('sp.mc1')} {meur(sotp.market_check.own_market_cap_eur)} {t('sp.mc2')}{' '}
            {num(sotp.market_check.price_vs_nav_pct, 1)}% {t('sp.mc3')}{tx(sotp.market_check.note, lang)}).</>
        )}
        {sotp.missing && sotp.missing.length > 0 && (
          <> · <span className="flag">{t('sp.missingFlag')}</span> {sotp.missing.map((x) => tx(x, lang)).join(', ')}</>
        )}
      </div>
    </section>
  )
}

function Fundamentals({ data }) {
  const { lang, t } = useLang()
  return (
    <section>
      <div className="sec-label">{t('sp.fundTitle1')}{data.fiscal_year || dash}{t('sp.fundTitle2')}</div>
      <table>
        <thead>
          <tr>
            <th>{t('fin.item')}</th><th className="num">{t('sp.colValue')}</th><th className="num">{t('sp.colConf')}</th><th>{t('common.source')}</th>
          </tr>
        </thead>
        <tbody>
          {data.fundamentals.map((f) => (
            <tr key={f.item}>
              <td>{tx(f.label, lang)}</td>
              <td className="num">
                {f.missing ? <span className="flag">{t('mkt.indicesNone')}</span>
                  : f.unit === 'pct' ? pct(f.value_eur, 2)
                    : f.unit === 'eur_per_share' ? eur(f.value_eur) : meur(f.value_eur)}
              </td>
              <td className={`num ${f.confidence !== null && f.confidence < 0.85 ? 'conf-low' : ''}`}>
                {f.missing ? dash
                  : f.confidence === null || f.confidence === undefined ? t('sp.derived') : num(f.confidence, 2)}
              </td>
              <td className="fund-src">
                {f.missing ? '' : (
                  <>
                    {f.source_page && f.source_page !== 'computed' ? `${f.source_page} ` : ''}
                    {f.source_page === 'computed' ? `${t('sp.computedFrom')} ` : ''}
                    {f.source_url ? <a href={f.source_url} target="_blank" rel="noreferrer">{t('sp.reportLink')}</a> : null}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="srcnote">{tx(data.metrics.basis_note, lang)}. {t('sp.fundNote')}</div>
    </section>
  )
}

export default function StockPage() {
  const { ticker } = useParams()
  const { lang, t } = useLang()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [tab, setTabRaw] = useState(() =>
    (typeof window !== 'undefined' && window.location.hash.slice(1)) || 'pregled')
  const setTab = (k) => { setTabRaw(k); try { window.history.replaceState(null, '', `#${k}`) } catch {} }

  // SEO: kanonske rute su lowercase (/dionica/koei, /en/stock/koei) — uppercase
  // varijanta se preusmjerava (replace, bez unosa u povijest); server radi 301
  useEffect(() => {
    if (ticker !== String(ticker).toLowerCase()) {
      const base = lang === 'en' ? '/en/stock/' : '/dionica/'
      navigate(`${base}${String(ticker).toLowerCase()}${window.location.hash}`,
        { replace: true })
    }
  }, [ticker, navigate, lang])

  useEffect(() => {
    setData(null); setErr(null)
    // statični export (frontend/public/data/<TICKER>.json) — bez API-ja i baze;
    // SPA rewrite vraća index.html za nepostojeći ticker, pa čuvamo content-type
    fetch(`/data/${String(ticker).toUpperCase()}.json`)
      .then((r) => {
        const isJson = (r.headers.get('content-type') || '').includes('json')
        if (!r.ok || !isJson) throw new Error(`${t('sp.noDataFor')} ${ticker}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setErr(String(e.message || e)))
  }, [ticker])

  useEffect(() => {
    if (data) {
      document.title = `${data.ticker} ${t('sp.docTitleMid')} ${data.name} ${t('sp.docTitleTail')}`
      try { localStorage.setItem('lastTicker', data.ticker) } catch {}
      // GTM konverzijski eventi: stock_view + engaged_reader (3+ različite
      // dionice u sesiji — brojimo u sessionStorage, pushamo jednom)
      pushEvent('stock_view', { ticker: data.ticker })
      try {
        const seen = new Set(JSON.parse(sessionStorage.getItem('bl_viewed') || '[]'))
        seen.add(data.ticker)
        sessionStorage.setItem('bl_viewed', JSON.stringify([...seen]))
        if (seen.size >= 3 && !sessionStorage.getItem('bl_engaged')) {
          sessionStorage.setItem('bl_engaged', '1')
          pushEvent('engaged_reader', { distinct_stocks: seen.size })
        }
      } catch { /* sessionStorage nedostupan -> preskoči */ }
    }
  }, [data, lang])

  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">

      {err && <section className="error">{t('common.error')}: {err}</section>}
      {!data && !err && <div className="loading">{t('sp.loading')} {ticker}…</div>}

      {data && (() => {
        const marketOnly = data.data_status === 'market_only'
        const rec = data.valuation?.reconciliation
        const zone = rec && rec.zone_low !== null && rec.zone_high !== null
          ? [rec.zone_low, rec.zone_high] : null
        /* v3 S: po-klasne zone iz iste vrijednosti firme (tržišni omjer) */
        const classZones = rec?.class_zones || null
        const primaryCls = data.share_classes.find((c) => c.is_primary) || data.share_classes[0]
        const pz = zone && classZones && classZones[primaryCls?.ticker]
        const zoneHdr = pz ? [pz.zone_low, pz.zone_high] : zone
        return (
        <>
          {/* ============ GORE · TRŽIŠNI PROFIL ============ */}
          <ProfileHeader data={{ ...data, sector_hr: sectorLabel(data.sector, lang) || data.sector }}
            zone={zoneHdr} />
          {data.business_profile?.activity && (
            <div className="prof-activity">
              <div className="prof-klabel">{t('sp.bpKlabel')}</div>
              <p>{data.business_profile.activity}
                {data.business_profile.activity_source_page &&
                  <span className="fund-src"> ({data.business_profile.activity_source_page})</span>}
                {lang === 'en' && <span className="fund-src"> {t('sp.hrSourceNote')}</span>}
              </p>
            </div>
          )}
          <IlliquidBanner liquidity={data.liquidity} />

          <TabBar tab={tab} setTab={setTab} ticker={data.ticker} />

          {/* ============ PREGLED ============ */}
          {tab === 'pregled' && (
          <>
          <PriceChart data={data} zone={zone} classZones={classZones} />
          <StatsStrip data={data} />
          <ClassExplainer data={data} />
          {!marketOnly && (
            <div className="fin3-grid">
              <FinChart trend={data.trend} />
              <BusinessProfile bp={data.business_profile} />
            </div>
          )}
          <Dividends data={data} />
          </>
          )}

          {/* ============ ANALIZA VRIJEDNOSTI ============ */}
          {tab === 'analiza' && (marketOnly ? (
            <AnalysisUnavailable note={data.data_note} />
          ) : (
          <>
          <AnchorPanel data={data} />
          <ValueVsBook note={data.valuation.value_vs_book} />
          <SecondaryList data={data} />
          <Risks risks={data.risks} />
          <Assumptions valuation={data.valuation} />
          <DividendSanity rec={rec} />
          <MarketImplied rec={rec} />

          <section>
            <div className="sec-label">{t('sp.valTitle')}</div>
            <p className="spread-lead">
              {data.valuation.reconciliation && data.valuation.reconciliation.divergent
                ? t('sp.leadDiv')
                : t('sp.leadCmp')}
            </p>
            <p className="spread-note">
              {t('sp.spreadNote')}
            </p>
            <VerdictSpread
              methods={data.valuation.ran}
              classes={data.share_classes}
              reconciliation={data.valuation.reconciliation}
              liquidity={data.liquidity}
            />
            <div className="srcnote">
              {t('sp.confPerMethod')}{' '}
              {data.valuation.ran.map((m, i) => (
                <React.Fragment key={m.key}>
                  {i > 0 && ' · '}
                  {tx(m.label, lang)} <b>{num(m.confidence, 1)}</b>
                </React.Fragment>
              ))}
            </div>
          </section>

          <div className="cols">
            <section className="narr">
              <div className="sec-label">{t('sp.whyDiverge')}</div>
              <Narrative data={data} />
            </section>
            <SotpTable sotp={data.valuation.sotp} />
          </div>

          <section>
            <div className="sec-label">{t('sp.skippedTitle')}</div>
            {data.valuation.skipped.map((s) => (
              <div className="skip" key={s.key}>
                <span className="m">{tx(s.label, lang)}</span>
                <span>{tx(s.reason, lang)}</span>
              </div>
            ))}
          </section>
          <Legend />
          </>
          ))}

          {/* ============ KLJUČNI POKAZATELJI ============ */}
          {tab === 'pokazatelji' && (marketOnly ? (
            <AnalysisUnavailable note={data.data_note} />
          ) : (
          <>
          <IndicatorGroups indicators={data.indicators} />
          <KeyIndicators data={data} />
          <Metrics data={data} />
          <Fundamentals data={data} />
          <Legend />
          </>
          ))}

          {/* ============ USPOREDBA ============ */}
          {tab === 'usporedba' && <Comparison data={data} />}

          {/* ============ IZVJEŠTAJI ============ */}
          {tab === 'izvjestaji' && (marketOnly ? (
            <AnalysisUnavailable note={data.data_note} />
          ) : (
          <>
          <div className="fin3-grid">
            <FinChart trend={data.trend} />
            <Fin3Y f3={data.financials_3y} />
          </div>
          <Balance b={data.balance} />
          <Segments seg={data.segments} />
          <BankKpi bk={data.bank_kpi} />
          </>
          ))}

          {/* ============ DIONIČARI ============ */}
          {tab === 'dionicari' && (
            <>
              <Ownership own={data.ownership} liquidity={data.liquidity} />
              <OmfHolders ticker={data.ticker} />
            </>
          )}

          {/* ============ NOVOSTI ============ */}
          {tab === 'novosti' && <NewsTab news={data.news} />}

          <MethodologyNote m={data.methodology} />

          <div className="disc">
            <b>{t('sp.disc1')}</b>{' '}
            {tx(data.mar_note, lang)} {t('sp.disc2')} <span className="flag">{t('sp.assumptionFlag')}</span> /{' '}
            <span className="ph">{t('sp.assumpShort')}</span> {t('sp.disc3')}
          </div>
        </>
        )
      })()}
      </main>
      <SiteFooter />
    </div>
  )
}
