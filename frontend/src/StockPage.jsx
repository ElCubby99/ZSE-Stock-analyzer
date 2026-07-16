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
import { dash, eur, meur, num, pct } from './format.js'

// live firme (orchestrator) + CROS/ZABA (M1–M5) + HPB/HT (samo tržišni profil)
const TICKERS = ['ADRS', 'CROS', 'ZABA', 'ADPL', 'ARNT', 'ATGR', 'DLKV', 'HPB',
  'HT', 'IG', 'KODT', 'KOEI', 'PODR', 'RIVP', 'SPAN', 'TOK', 'ZITO']

const SECTOR_HR = {
  holding: 'Holding', insurance: 'Osiguranje', tourism: 'Turizam',
  consumer: 'Konzumeri', industrial: 'Industrija', bank: 'Banka',
  telecom: 'Telekomunikacije', technology: 'Tehnologija', energy: 'Energetika',
  shipping: 'Brodarstvo', aquaculture: 'Marikultura', fund: 'Fond (ZAIF)',
  transport: 'Promet', construction: 'Graditeljstvo', real_estate: 'Nekretnine',
  other: 'Ostalo',
}

// leće metoda za naraciju raskoraka (opis mehanike, ne preporuka)
const LENS = {
  multiples_relative: 'peer multipli primijenjeni na zaradu i knjigu',
  ddm_gordon: 'kapitalizirana stvarna dividenda uz r i g',
  justified_pb_roe: 'knjigovodstvena vrijednost skalirana vlastitim ROE-om',
  residual_income: 'knjiga + diskontirani višak povrata iznad troška kapitala (ROE fejda prema COE)',
  sotp_nav: 'tržišna vrijednost dijelova (udjeli + segmenti) umanjena za holding diskont',
  ev_ebitda: 'EV/EBITDA multipla',
  dcf_fcf: 'diskontirani slobodni novčani tok',
}

function classCss(i) { return i === 0 ? 'ord' : 'prf' }

// M8: arhetipovi i imena metoda za naraciju sidrene fer-zone
const ARCH_HR = { holding: 'holding', capital: 'banka/osiguranje — kapitalno sidro',
  operating: 'operativna firma' }
const METHOD_HR = {
  sotp_nav: 'SOTP/NAV', residual_income: 'rezidualni dohodak',
  justified_pb_roe: 'opravdani P/B', dcf_fcf: 'DCF',
  multiples_relative: 'relativni multipli', ev_ebitda: 'EV/EBITDA',
  ddm_gordon: 'dividendni diskont',
}

/* ---------- v2 sekcije ---------- */

/* M9: mini trend prihoda i EBITDA-e (barovi iz baze) + ČINJENIČNA naracija */
function TrendBlock({ trend }) {
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
      <div className="sec-label">Trend — {trend.revenue_label.toLowerCase()} i EBITDA</div>
      <div className="trend-grid">
        <svg viewBox={`0 0 ${W} ${H}`} className="trend-svg" role="img"
          aria-label="Trend prihoda i EBITDA-e">
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
          <p className="trend-narr">{trend.narration}</p>
          <div className="legend">
            <span><i className="swatch" style={{ background: '#2F5D86' }} /> {trend.revenue_label} (M€)</span>
            <span><i className="swatch" style={{ background: '#1F6E5A' }} /> EBITDA (M€)</span>
          </div>
        </div>
      </div>
      <div className="subnote">{trend.note}.</div>
    </section>
  )
}

/* M9: profil poslovanja — SAMO činjenice iz izvješća; epiteti = tvrdnje
   izdavatelja, označene i citirane. Bez izvora -> sekcija kaže "nema u bazi". */
function BusinessProfile({ bp }) {
  return (
    <section>
      <div className="sec-label">
        {bp?.generic ? 'Profil poslovanja' : 'Profil poslovanja — iz godišnjeg izvješća'}
        {bp?.generic && <span className="flag" style={{ marginLeft: 8 }}>generički opis</span>}
      </div>
      {!bp ? (
        <div className="subnote"><span className="flag">nema u bazi</span>{' '}
          profil poslovanja još nije ekstrahiran iz izvješća — ništa se ne generira.</div>
      ) : bp.generic ? (
        <>
          <p className="bp-activity">{bp.activity}</p>
          <div className="subnote">{bp.note}.</div>
        </>
      ) : (
        <>
          <p className="bp-activity">{bp.activity}
            {bp.activity_source_page && <span className="fund-src"> ({bp.activity_source_page})</span>}
          </p>
          <div className="bp-grid">
            {bp.segments.length > 0 && (
              <div>
                <div className="bp-h">Glavni segmenti</div>
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
                  <div className="bp-h">Tržišta</div>
                  <ul className="bp-list">
                    {bp.markets.map((m) => (
                      <li key={m.market}>{m.market}
                        {m.source_page && <span className="fund-src"> ({m.source_page})</span>}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <div className="bp-h">Izvozni udio</div>
              {bp.export_share ? (
                <p className="bp-export">
                  <b>{num(bp.export_share.value * 100, 0)}%</b> — {bp.export_share.basis}
                  {bp.export_share.source_page && <span className="fund-src"> ({bp.export_share.source_page})</span>}
                </p>
              ) : (
                <p className="bp-export"><span className="np">nije objavljen u izvješću</span></p>
              )}
            </div>
          </div>
          {bp.issuer_claims.length > 0 && (
            <div className="bp-claims">
              <div className="bp-h">Tvrdnje izdavatelja (necjenjeno, citirano)</div>
              <ul className="bp-list">
                {bp.issuer_claims.map((c, i) => (
                  <li key={i}>
                    <span className="flag">tvrdnja izdavatelja</span> {c.claim}
                    {c.source_page && <span className="fund-src"> ({c.source_page})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="subnote">{bp.note}. Izvor: {bp.source}.</div>
        </>
      )}
    </section>
  )
}

function Fin3Y({ f3 }) {
  if (!f3 || !f3.years.length) return null
  const fmtVal = (r, y) => {
    const v = r.values[String(y)]
    if (v === null || v === undefined) return <span className="flag">nema u bazi</span>
    return r.unit === 'eur_per_share' ? eur(v) : meur(v)
  }
  const pctCell = (v) => {
    if (v === null || v === undefined) return <td className="num">{dash}</td>
    return <td className={`num ${v >= 0 ? 'pos' : 'neg'}`}>{v >= 0 ? '+' : ''}{num(v * 100, 1)}%</td>
  }
  return (
    <section>
      <div className="sec-label">Financije — {f3.years.length} godine, konsolidirano</div>
      <table>
        <thead>
          <tr>
            <th>Stavka</th>
            {f3.years.map((y) => <th className="num" key={y}>FY{y}</th>)}
            <th className="num">YoY</th><th className="num">CAGR</th>
          </tr>
        </thead>
        <tbody>
          {f3.rows.map((r) => (
            <tr key={r.item}>
              <td>{r.label}</td>
              {f3.years.map((y) => <td className="num" key={y}>{fmtVal(r, y)}</td>)}
              {pctCell(r.yoy_pct)}
              {pctCell(r.cagr_pct)}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="subnote">{f3.note}. YoY = zadnja godina prema prethodnoj; CAGR preko prikazanog razdoblja.</div>
    </section>
  )
}

function Balance({ b }) {
  if (!b) return null
  const lev = b.leverage
  return (
    <section>
      <div className="sec-label">Bilanca i zaduženost — FY{b.fiscal_year}</div>
      <div className="kv">
        <div className="cell"><div className="k">Ukupna imovina</div><div className="v">{meur(b.total_assets, 0)}</div></div>
        <div className="cell"><div className="k">Kapital matici</div><div className="v">{meur(b.equity_parent, 0)}</div></div>
        <div className="cell"><div className="k">Knjiga / dionici</div><div className="v">{eur(b.bvps)}</div></div>
        {b.is_financial ? (
          <div className="cell">
            <div className="k">Neto dug / EBITDA</div>
            <div className="v np">n/p</div>
          </div>
        ) : (
          <>
            <div className="cell">
              <div className="k">Neto dug</div>
              <div className="v">{lev && lev.net_debt !== null ? meur(lev.net_debt, 0) : dash}</div>
              <div className="n">{lev?.components_note}</div>
            </div>
            <div className="cell">
              <div className="k">Neto dug / EBITDA</div>
              <div className="v">{lev && lev.net_debt_to_ebitda !== null ? `${num(lev.net_debt_to_ebitda, 2)}×` : dash}</div>
            </div>
          </>
        )}
      </div>
      {b.leverage_note && <div className="subnote">{b.leverage_note}</div>}
      {!b.is_financial && lev?.current_ratio === null && (
        <div className="subnote">{lev.current_ratio_note}.</div>
      )}
    </section>
  )
}

function Segments({ seg }) {
  if (!seg) return null
  const rec = seg.reconciliation
  return (
    <section>
      <div className="sec-label">Segmenti (IFRS 8) — FY{seg.fiscal_year}</div>
      <table>
        <thead>
          <tr><th>Segment</th><th className="num">Prihod</th><th className="num">EBITDA</th>
            <th className="num">EBITDA marža</th><th className="num">Neto dobit</th></tr>
        </thead>
        <tbody>
          {seg.rows.map((r) => (
            <tr key={r.key}>
              <td>{r.label} <span className="fund-src">{r.source_page ? '' : ''}</span></td>
              <td className="num">{meur(r.revenue, 0)}</td>
              <td className="num">{r.ebitda === null ? <span className="np">n/p</span> : meur(r.ebitda, 1)}</td>
              <td className="num">{r.ebitda_margin === null ? dash : pct(r.ebitda_margin)}</td>
              <td className="num">{meur(r.net_result, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rec && (
        <div className="subnote">
          {rec.revenue_comparable ? (
            <>Σ prihoda segmenata {meur(rec.revenue_sum, 0)} vs grupa {meur(rec.group_revenue, 0)}
              {rec.revenue_residual !== null && <> → razlika {meur(rec.revenue_residual, 0)} = eliminacije/centar</>}. </>
          ) : (
            <>Reconciliation prihoda: <span className="np">{rec.revenue_note}</span>. </>
          )}
          {rec.note}.
        </div>
      )}
    </section>
  )
}

function BankKpi({ bk }) {
  if (!bk) return null
  return (
    <section>
      <div className="sec-label">Bankovni pokazatelji — FY{bk.fiscal_year}</div>
      <div className="kv">
        {bk.kpis.map((k) => (
          <div className="cell" key={k.key}>
            <div className="k">{k.label}</div>
            <div className="v">
              {k.missing ? <span className="flag">nema u bazi</span> : pct(k.value, 2)}
            </div>
            <div className="n">{k.basis}</div>
          </div>
        ))}
      </div>
      <div className="subnote">{bk.note}.</div>
    </section>
  )
}

const hrDate = (iso) => {
  if (!iso) return dash
  const [y, m, d] = iso.split('-')
  return `${Number(d)}.${Number(m)}.${y}.`
}

function ChangeCell({ r, hasPrev }) {
  if (!hasPrev) return <span>{dash}</span>
  if (r.entered) return <span className="okflag">ušao u top 10</span>
  if (r.change_pp === null || r.change_pp === undefined) return <span>{dash}</span>
  const v = r.change_pp
  const sign = v > 0 ? '+' : v < 0 ? '−' : '±'
  const col = v > 0 ? '#1F6E5A' : v < 0 ? '#9E2B25' : 'rgba(38,46,51,0.55)'
  return <span style={{ color: col }}>{sign}{num(Math.abs(v), 2)} p.p.</span>
}

function Top10({ t10 }) {
  if (!t10) return null
  const hasPrev = !!t10.prev_snapshot_date
  return (
    <section>
      <div className="sec-label">Top 10 dioničara</div>
      <div className="subnote" style={{ marginBottom: 8 }}>
        Snapshot {hrDate(t10.snapshot_date)} — {t10.source_label}.
        {hasPrev
          ? <> Promjene vs snapshot {hrDate(t10.prev_snapshot_date)} ({t10.prev_source_label}).</>
          : <> {t10.note}.</>}
      </div>
      <table>
        <thead>
          <tr>
            <th>#</th><th>Imatelj (kako je objavljen)</th>
            <th className="num">Udjel</th>
            <th className="num">Promjena{hasPrev ? ' (p.p.)' : ''}</th>
            <th>Izvor</th>
          </tr>
        </thead>
        <tbody>
          {t10.rows.map((r) => (
            <tr key={r.rank}>
              <td>{r.rank}.</td>
              <td>
                {r.name}
                {r.is_custody && <> <span className="ph">skrbnički / zbirni račun</span></>}
                {r.prev_name && (
                  <div className="fund-src">uspoređeno s: {r.prev_name}</div>
                )}
              </td>
              <td className="num">{num(r.pct, 2)} %</td>
              <td className="num"><ChangeCell r={r} hasPrev={hasPrev} /></td>
              <td className="fund-src">{r.source_detail}</td>
            </tr>
          ))}
          {t10.free_float_from_top10_pct !== null && t10.free_float_from_top10_pct !== undefined && (
            <tr className="sotp-total">
              <td /><td>Free float ≈ 100 % − Σ top 10 (aproksimacija)</td>
              <td className="num">{num(t10.free_float_from_top10_pct, 2)} %</td>
              <td /><td />
            </tr>
          )}
        </tbody>
      </table>
      {hasPrev && !!(t10.left || []).length && (
        <div className="subnote">
          Izašli iz top 10 od {hrDate(t10.prev_snapshot_date)}: {t10.left.join(' · ')}.
        </div>
      )}
      <div className="subnote">
        {t10.custody_note}. Imena su prikazana točno kako su javno objavljena
        (SKDD / godišnje izvješće) — ne dopunjavaju se.
      </div>
    </section>
  )
}

function Ownership({ own, liquidity }) {
  if (!own) return null
  const anyFlag = (liquidity?.classes || []).some((c) => c.flag !== 'ok')
  return (
    <>
    <Top10 t10={own.top10} />
    <section>
      <div className="sec-label">Vlasnički graf i free float</div>
      {own.holders.length ? (
        <>
          <table>
            <thead><tr><th>Imatelj</th><th className="num">Udjel</th><th>Izvor</th></tr></thead>
            <tbody>
              {own.holders.map((h) => (
                <tr key={h.name}>
                  <td>{h.name}{h.ticker ? ` (${h.ticker})` : ''}</td>
                  <td className="num">{pct(h.pct, 2)}</td>
                  <td className="fund-src">{h.source}</td>
                </tr>
              ))}
              <tr className="sotp-total">
                <td>Free float (približno)</td>
                <td className="num">{pct(own.free_float_pct_approx, 1)}</td>
                <td />
              </tr>
            </tbody>
          </table>
          <div className="subnote">
            {own.note}.
            {own.liquidity_link && anyFlag && <> <b>{own.liquidity_link}.</b></>}
          </div>
        </>
      ) : own.top10 ? (
        <div className="subnote">
          Vlasnički graf (povezana uvrštena društva) nema unosa za ovu firmu —
          free float je izveden iz tablice top 10 iznad.
        </div>
      ) : (
        <div className="subnote"><span className="flag">nema u bazi</span> {own.note}.</div>
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
  const m = data.metrics
  return (
    <div className="metrics">
      <div className="metric">
        <div className="k">Dobit / dionici</div>
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
        <div className="k">Div. prinos</div><div className="v">{dash}</div>
        <div className="split"><Split perClass={m.per_class} field="div_yield" fmt={(v) => pct(v, 2)} /></div>
        {m.dps_label && <div className="split">{m.dps_label}</div>}
      </div>
      <div className="metric">
        <div className="k">Tržišna kap.</div>
        <div className="v">{m.market_cap_eur ? `${num(m.market_cap_eur / 1e6, 0)} M€` : dash}</div>
        <div className="split">{data.share_classes.length > 1 ? 'sve klase' : 'jedna klasa'}</div>
      </div>
      <div className="metric">
        <div className="k">EBITDA</div>
        <div className="v">{m.ebitda_eur ? `${num(m.ebitda_eur / 1e6, 0)} M€` : dash}</div>
        <div className="split">ROE {pct(m.roe)}</div>
      </div>
    </div>
  )
}

/* v3 A (Borisov zahtjev): test održive dividende — for-dummies raspis s
   brojkama OVE dionice, kod svake dionice gdje je test primjenjiv.
   Struktura: što je D_sust -> što je donji rub -> što je implicirani
   prinos -> koji je prag i zašto (Gordonova logika) -> verdikt. */
function DividendSanity({ rec }) {
  const ds = rec?.dividend_sanity
  if (!ds) return null
  const ok = ds.verdict === 'prolazi'
  return (
    <section>
      <div className="sec-label">Test održive dividende — običnim jezikom</div>
      <div className="controls">
        <div className="ctrl">
          <div className="top">
            <span className="name">Održiva dividenda (D_sust)</span>
            <span className="out mono">{num(ds.d_sust_ps, 2)} €</span>
          </div>
          <div className="plain">
            Naša procjena dividende koju firma može isplaćivati <b>trajno</b> —
            ne zadnja isplaćena, nego: održivi udio dobiti koji ide dioničarima
            (medijan povijesnih isplata, računan samo nad redovnima — jednokratne
            i isplate iz zadržane dobiti ne ulaze; kod banaka najviše 70%) ×
            dobit zadnjih 12 mjeseci ÷ broj dionica.
          </div>
        </div>
        <div className="ctrl">
          <div className="top">
            <span className="name">Prinos na donjem rubu zone</span>
            <span className="out mono">{num(ds.implied_yield_low * 100, 1)} %</span>
          </div>
          <div className="plain">
            Donji rub je najniža cijena koju naš model još smatra fer
            ({num(ds.zone_low, 2)} €). Tko bi dionicu kupio baš po toj cijeni,
            samo od održive dividende dobivao bi {num(ds.d_sust_ps, 2)} € /
            {' '}{num(ds.zone_low, 2)} € = <b>{num(ds.implied_yield_low * 100, 1)} %</b> godišnje.
          </div>
        </div>
        <div className="ctrl">
          <div className="top">
            <span className="name">Dopušteni prag (r − g)</span>
            <span className="out mono">{num(ds.threshold * 100, 1)} %</span>
          </div>
          <div className="plain">
            Ako dividenda trajno raste stopom g, vrijednost dionice ne može biti
            manja od D ÷ (r − g) — jer već sama dividenda na toj cijeni
            isporučuje prinos r koji ulagač traži za rizik. Obrnuto: prinos iz
            održive dividende na fer cijeni ne smije biti veći od r − g.
            Ovdje: traženi prinos r = {num(ds.r * 100, 2)} % minus {ds.g_source}
            {' '}= <b>{num(ds.threshold * 100, 1)} %</b>.
          </div>
        </div>
        <div className="ctrl">
          <div className="top">
            <span className="name">Rezultat testa</span>
            <span className="out">{ok
              ? <span className="okflag">PROLAZI</span>
              : <span className="flag">U REKALIBRACIJI ({ds.verdict.toUpperCase()})</span>}</span>
          </div>
          <div className="plain">
            {ok
              ? `Prinos ${num(ds.implied_yield_low * 100, 1)} % je unutar dopuštenog (${num(ds.threshold * 100, 1)} %) — održiva dividenda ne pobija zonu.`
              : ds.verdict === 'preniska'
                ? `Prinos ${num(ds.implied_yield_low * 100, 1)} % je VEĆI od praga ${num(ds.threshold * 100, 1)} % — model bi tvrdio apsurd ("kupi po ${num(ds.zone_low, 2)} € i sama dividenda ti nosi više nego što tražiš za rizik"), pa je donji rub vjerojatno prenizak i zonu ne objavljujemo dok se ulazi ne razriješe.`
                : 'Uz payout blizu 100% prinos na gornjem rubu je premalen — zona je vjerojatno previsoka i ne objavljujemo je dok se ulazi ne razriješe.'}
            {' '}Test je činjenična unutarnja kontrola modela, ne preporuka.
          </div>
        </div>
      </div>
    </section>
  )
}

function Assumptions({ valuation }) {
  const p = valuation.params
  /* dvorazinski princip: jedna rečenica OBIČNIM jezikom vidljiva,
     tehnički izvod (CAPM, izvori, citati) iza klika — izračun se ne mijenja */
  /* v3 FAZA K: puni raspis r-a — rf + β×ERP + CRP + nelikvidnost = r,
     svaka komponenta zasebna kartica s izvorom iza klika */
  const hasStack = p.rf !== null && p.rf !== undefined && p.crp !== null && p.crp !== undefined
  const rFormula = hasStack
    ? `${num(p.rf * 100, 2)} % + ${num(p.beta, 2)} × ${num(p.erp * 100, 2)} %`
      + ` + ${num(p.crp * 100, 1)} p.b.`
      + (p.illiq_premium ? ` + ${num(p.illiq_premium * 100, 1)} p.b.` : '')
      + ` = ${pct(p.r, 2)}`
    : null
  const cards = [
    {
      name: 'Trošak kapitala r', out: pct(p.r, 2), src: p.sources.r, sure: p.rates_calibrated,
      plain: `Trošak kapitala ${pct(p.r, 2)} — prinos koji ulagač razumno traži za rizik ove dionice. Veći = stroža (niža) procjena.`
        + (rFormula ? ` Raspis: rf + β×ERP + CRP${p.illiq_premium ? ' + nelikvidnost' : ''} = ${rFormula}.` : ''),
    },
  ]
  if (hasStack) {
    cards.push({
      name: 'Bezrizični prinos rf', out: pct(p.rf, 2), src: p.sources.rf || p.sources.r, sure: false,
      plain: `Prinos "bez rizika" u euru (10-godišnji njemački Bund) — temelj od kojeg svaki zahtijevani prinos kreće. Rizik Hrvatske NIJE ovdje — on je zasebna stavka (CRP), da se ne bi računao dvaput.`,
    })
    cards.push({
      name: 'Premija tržišta ERP', out: pct(p.erp, 2), src: p.sources.erp || p.sources.r, sure: false,
      plain: `Koliko ulagači povrh bezrizičnog prinosa traže za ulaganje u dionice općenito (zrelo tržište, bez premije zemlje). Množi se betom dionice.`,
    })
    cards.push({
      name: 'Premija zemlje CRP', out: `+${num(p.crp * 100, 1)} p.b.`, src: p.sources.crp || p.sources.r, sure: false,
      plain: `Mali dodatak za rizik Hrvatske — primjeren investment-grade eurozoni ('A-'). Računa se točno jednom: nije skriven ni u rf-u ni u ERP-u.`,
    })
  }
  cards.push({
    name: 'Dugoročni rast g', src: p.sources.g, sure: p.rates_calibrated,
    out: p.g_terminal ? `${pct(p.g, 1)} · ${pct(p.g_terminal, 1)}` : pct(p.g, 1),
    plain: `Dugoročni rast — koliko firma raste "zauvijek" nakon razdoblja projekcije; vezan uz rast gospodarstva i inflaciju (${pct(p.g, 1)} za kapitalne metode, ${p.g_terminal ? pct(p.g_terminal, 1) : dash} terminal za DCF).`,
  })
  if (p.beta !== null && p.beta !== undefined) {
    cards.push({
      name: 'Beta (β)', out: num(p.beta, 2), src: p.sources.r, sure: p.beta_calibrated,
      badge: p.beta_origin || null, // Z1: regresija / sektorska / clamp
      plain: `Beta ${num(p.beta, 2)} — koliko dionica njiše u odnosu na tržište: 1 = kao tržište, više = jače njihanje (rizičnije).`,
    })
  }
  if (p.illiq_premium) {
    cards.push({
      name: 'Premija nelikvidnosti', out: `+${num(p.illiq_premium * 100, 1)} p.b.`,
      src: p.illiq_src || p.sources.r, sure: true,
      plain: `Dodatak na trošak kapitala jer se dionicom slabo trguje — izlazak iz pozicije nosi stvaran trošak (širok spread, plitka knjiga naloga). Strože (niže) sidri procjenu.`,
    })
  }
  if (valuation.sotp) {
    /* v2 §4: prikaži STVARNO primijenjeni diskont s razlogom iz taksonomije */
    const reason = p.holding_discount_reason || ''
    const operating = reason.includes('integrirani operativni parent')
    const measured = reason.includes('IZMJERENI')
    cards.push({
      name: 'Holding diskont',
      out: `${num(p.holding_discount_low * 100, 0)}–${num(p.holding_discount_high * 100, 0)}%`,
      src: reason || p.sources.holding_discount,
      sure: operating || measured,
      plain: operating
        ? 'Bez holding popusta — integrirani operativni parent: kontrolira i konsolidira kćeri iste djelatnosti, pa se ne tretira kao pasivni holding (raspon 0–5% je samo osjetljivost).'
        : measured
          ? 'Popust izmjeren iz povijesti vlastite cijene prema vrijednosti dijelova (P/NAV) — tržište povijesno plaća premiju, pa se popust klampa na 0.'
          : 'Holding popust — burza pasivne holdinge obično vrednuje ispod zbroja dijelova (trošak centrale, dvostruko oporezivanje, slabija likvidnost).',
    })
  }
  cards.push({
    name: p.peers_narrow ? 'Peer multipli (P/E · P/B) — uski skup (n=2)'
      : 'Peer multipli (P/E · P/B)',
    out: `${num(p.peer_pe, 2)} · ${num(p.peer_pb, 2)}`,
    src: p.sources.peers, sure: p.peers_calibrated && !p.peers_narrow,
    plain: p.peers_narrow
      ? 'Usporedive firme — medijan SAMO DVIJU firmi (uski skup), pa je pouzdanost snižena; koliko tržište plaća po euru zarade (P/E) i knjige (P/B).'
      : 'Usporedive firme — koliko tržište plaća po euru zarade (P/E) i knjige (P/B) kod sličnih firmi; to primjenjujemo na ovu firmu.',
  })
  return (
    <section>
      <div className="sec-label">Pretpostavke — običnim jezikom, s izvorom iza klika</div>
      <div className="controls">
        {cards.map((c) => (
          <div className="ctrl" key={c.name}>
            <div className="top">
              <span className="name">
                {c.name}{' '}
                {c.sure ? <span className="okflag">izvor</span> : <span className="flag">pretpostavka</span>}
                {c.badge && <span className="beta-badge">{c.badge}</span>}
              </span>
              <span className="out mono">{c.out}</span>
            </div>
            <div className="plain">{c.plain}</div>
            <details className="src-details">
              <summary>tehnički izvod i izvor</summary>
              <div className="src">{c.src || 'izvor nije zabilježen'}</div>
            </details>
          </div>
        ))}
      </div>
      <ul className="flaglist">
        {valuation.assumption_flags.map((f) => (
          <li key={f.key}>
            {f.status === 'izvor'
              ? <span className="okflag">izvor</span>
              : <span className="flag">pretpostavka</span>} {f.label} — {f.why}
          </li>
        ))}
      </ul>
    </section>
  )
}

/* v2 §7: objašnjenje klasa — prava, zašto se cijene razlikuju; fer je
   klasno-agnostičan pa se premija redovne prikazuje, ne ugrađuje */
function ClassExplainer({ data }) {
  const ex = data.share_class_explainer
  if (!ex) return null
  return (
    <section>
      <div className="sec-label">Klase dionica — prava i zašto se cijene razlikuju</div>
      <table>
        <thead><tr><th>Klasa</th><th>Tip</th><th>Prava</th></tr></thead>
        <tbody>
          {ex.rows.map((r) => (
            <tr key={r.ticker}>
              <td><b>{r.ticker}</b></td>
              <td>{r.type}</td>
              <td>{r.rights}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="subnote">{ex.note}</div>
    </section>
  )
}

function Narrative({ data }) {
  const rec = data.valuation.reconciliation
  const ran = data.valuation.ran.filter((m) => !m.no_value)
  if (!rec || ran.length < 2) {
    return <p>Premalo metoda s vrijednošću za usporedbu — vidi tablicu fundamenata i preskočene metode.</p>
  }
  const byBase = [...ran].sort((a, b) => a.base - b.base)
  const lo = byBase[0]; const hi = byBase[byBase.length - 1]
  const sotp = ran.find((m) => m.key === 'sotp_nav')
  return (
    <>
      <p>
        Najnižu središnju vrijednost daje <b>{lo.label}</b> ({eur(lo.base, 0)}) — {LENS[lo.key]}.
        Najvišu daje <b>{hi.label}</b> ({eur(hi.base, 0)}) — {LENS[hi.key]}.
      </p>
      {sotp && data.is_group && sotp.key !== lo.key && (
        <p className="pull">
          SOTP gleda kroz maticu na tržišnu vrijednost udjela; metode vezane uz knjigu i dividendu
          taj dio ne hvataju. Raskorak između tih leća odražava holding prirodu društva.
        </p>
      )}
      <p>
        Fer-zona je <b>sidrena arhetipom</b> ({ARCH_HR[rec.archetype] || rec.archetype}
        {rec.anchor_methods?.length ? `: ${rec.anchor_methods.map((k) => METHOD_HR[k] || k).join(', ')}` : ''}):{' '}
        {eur(rec.zone_low, 0)}–{eur(rec.zone_high, 0)} po dionici
        (disperzija sidra {num(rec.dispersion * 100, 0)}%).
        {rec.zone_note ? ` ${rec.zone_note}.` : ''}
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
            Sekundarne leće izvan zone:{' '}
            {secOut.map((m, i) => (
              <React.Fragment key={m.key}>
                {i > 0 && ', '}
                {m.label} ({num(rec.method_roles[m.key].vs_zone_pct * 100, 0)}%)
              </React.Fragment>
            ))}
            {note ? ` — ${note}.` : '.'}
            {' '}Raspon svih metoda: {eur(rec.all_methods_low, 0)}–{eur(rec.all_methods_high, 0)}.
          </p>
        )
      })()}
      <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
        Koja je leća mjerodavna ovisi o tome što društvo jest (operativna firma, holding, osiguratelj);
        procjenu prepuštamo čitatelju. Pretpostavke i izvori svake metode navedeni su iznad.
      </p>
    </>
  )
}

const IDENTITY_BASIS = {
  our_estimate: 'naša procjena', market_fallback: 'tržišna (fallback)',
  multiple: 'multipl', izvještaj: 'izvještaj',
}

function SotpTable({ sotp }) {
  if (!sotp) return null
  if (sotp.identity) {
    // v2 §5: reconciliation identitet — svaka stavka s osnovom, per-share
    return (
      <section>
        <div className="sec-label">SOTP — identitet po stavkama (v2 §5)</div>
        <table>
          <thead><tr><th>Stavka</th><th className="num">M€</th>
            <th className="num">€/dionici</th><th>Osnova</th></tr></thead>
          <tbody>
            {sotp.identity.map((row, i) => (
              <tr key={i}>
                <td>{row.item}</td>
                <td className="num">{meur(row.eur)}</td>
                <td className="num">{row.per_share === null || row.per_share === undefined
                  ? dash : num(row.per_share, 2)}</td>
                <td><span className="basis">{IDENTITY_BASIS[row.basis] || row.basis}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="subnote">
          {sotp.identity_note}. {sotp.missing ? `Izvan NAV-a: ${sotp.missing.join('; ')}.` : ''}
          {sotp.parent_child_mismatch
            ? <span className="flag" style={{ marginLeft: 6 }}>MISMATCH: {sotp.parent_child_mismatch}</span>
            : null}
        </div>
      </section>
    )
  }
  return (
    <section>
      <div className="sec-label">SOTP — vrijednost po dijelu</div>
      <table>
        <tbody>
          {sotp.parts.map((part) => (
            <tr key={part.name}>
              <td>
                {part.name}{' '}
                {part.placeholder ? <span className="ph">pretp.</span> : null}
              </td>
              <td className="num">{meur(part.value_eur)}</td>
            </tr>
          ))}
          {sotp.net_cash && (
            <tr>
              <td>Neto novac <span className="basis">({sotp.net_cash.basis})</span></td>
              <td className="num">{meur(sotp.net_cash.value_eur)}</td>
            </tr>
          )}
          <tr className="sotp-total">
            <td>NAV (prije diskonta)</td>
            <td className="num">{meur(sotp.nav_total_eur)}</td>
          </tr>
        </tbody>
      </table>
      <div className="srcnote">
        Diskont {sotp.holding_discount_range
          ? `${num(sotp.holding_discount_range[0] * 100, 0)}–${num(sotp.holding_discount_range[1] * 100, 0)}%`
          : dash} — {sotp.holding_discount_reason}
        {sotp.market_check && (
          <> · Tržišna provjera: kapitalizacija {meur(sotp.market_check.own_market_cap_eur)} je{' '}
            {num(sotp.market_check.price_vs_nav_pct, 1)}% u odnosu na ovaj NAV ({sotp.market_check.note}).</>
        )}
        {sotp.missing && sotp.missing.length > 0 && (
          <> · <span className="flag">nedostaje</span> {sotp.missing.join(', ')}</>
        )}
      </div>
    </section>
  )
}

function Fundamentals({ data }) {
  return (
    <section>
      <div className="sec-label">Fundamenti — FY{data.fiscal_year || dash}, konsolidirano</div>
      <table>
        <thead>
          <tr>
            <th>Stavka</th><th className="num">Vrijednost</th><th className="num">Pouzdanost</th><th>Izvor</th>
          </tr>
        </thead>
        <tbody>
          {data.fundamentals.map((f) => (
            <tr key={f.item}>
              <td>{f.label}</td>
              <td className="num">
                {f.missing ? <span className="flag">nema u bazi</span>
                  : f.unit === 'pct' ? pct(f.value_eur, 2)
                    : f.unit === 'eur_per_share' ? eur(f.value_eur) : meur(f.value_eur)}
              </td>
              <td className={`num ${f.confidence !== null && f.confidence < 0.85 ? 'conf-low' : ''}`}>
                {f.missing ? dash
                  : f.confidence === null || f.confidence === undefined ? 'izvedeno' : num(f.confidence, 2)}
              </td>
              <td className="fund-src">
                {f.missing ? '' : (
                  <>
                    {f.source_page && f.source_page !== 'computed' ? `${f.source_page} ` : ''}
                    {f.source_page === 'computed' ? 'izračun iz objavljenih stavki ' : ''}
                    {f.source_url ? <a href={f.source_url} target="_blank" rel="noreferrer">izvješće</a> : null}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="srcnote">{data.metrics.basis_note}. Pouzdanost „izvedeno“ = brojka izračunata
        iz objavljenih stavki (npr. EBITDA = EBIT + amortizacija; neto dug = dug − novac).</div>
    </section>
  )
}

export default function StockPage() {
  const { ticker } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [tab, setTabRaw] = useState(() =>
    (typeof window !== 'undefined' && window.location.hash.slice(1)) || 'pregled')
  const setTab = (k) => { setTabRaw(k); try { window.history.replaceState(null, '', `#${k}`) } catch {} }

  // SEO: kanonske rute su lowercase (/dionica/koei) — uppercase varijanta se
  // preusmjerava (replace, bez unosa u povijest); server dodatno radi 301
  useEffect(() => {
    if (ticker !== String(ticker).toLowerCase()) {
      navigate(`/dionica/${String(ticker).toLowerCase()}${window.location.hash}`,
        { replace: true })
    }
  }, [ticker, navigate])

  useEffect(() => {
    setData(null); setErr(null)
    // statični export (frontend/public/data/<TICKER>.json) — bez API-ja i baze;
    // SPA rewrite vraća index.html za nepostojeći ticker, pa čuvamo content-type
    fetch(`/data/${String(ticker).toUpperCase()}.json`)
      .then((r) => {
        const isJson = (r.headers.get('content-type') || '').includes('json')
        if (!r.ok || !isJson) throw new Error(`nema podataka za ${ticker}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setErr(String(e.message || e)))
  }, [ticker])

  useEffect(() => {
    if (data) {
      document.title = `${data.ticker} dionica — ${data.name} | cijena, analiza vrijednosti, fer-zona | Burzovni list`
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
  }, [data])

  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">

      {err && <section className="error">Greška: {err}</section>}
      {!data && !err && <div className="loading">učitavam {ticker}…</div>}

      {data && (() => {
        const marketOnly = data.data_status === 'market_only'
        const rec = data.valuation?.reconciliation
        /* v3 A: "u rekalibraciji" — zonu ne prikazujemo kao mjerodavnu */
        const recal = rec?.recalibrating || null
        const zone = !recal && rec && rec.zone_low !== null && rec.zone_high !== null
          ? [rec.zone_low, rec.zone_high] : null
        return (
        <>
          {/* ============ GORE · TRŽIŠNI PROFIL ============ */}
          <ProfileHeader data={{ ...data, sector_hr: SECTOR_HR[data.sector] || data.sector }}
            zone={zone} recal={recal} />
          {data.business_profile?.activity && (
            <div className="prof-activity">
              <div className="prof-klabel">PROFIL POSLOVANJA</div>
              <p>{data.business_profile.activity}
                {data.business_profile.activity_source_page &&
                  <span className="fund-src"> ({data.business_profile.activity_source_page})</span>}
              </p>
            </div>
          )}
          <IlliquidBanner liquidity={data.liquidity} />

          <TabBar tab={tab} setTab={setTab} />

          {/* ============ PREGLED ============ */}
          {tab === 'pregled' && (
          <>
          <PriceChart data={data} zone={zone} />
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
          {recal && (
            <section className="prof-illiq" style={{ marginTop: 10 }}>
              <span className="prof-illiq-t">FER-ZONA U REKALIBRACIJI</span>
              <span className="prof-illiq-n">{recal}</span>
            </section>
          )}
          <AnchorPanel data={data} />
          <SecondaryList data={data} />
          <Risks risks={data.risks} />
          <Assumptions valuation={data.valuation} />
          <DividendSanity rec={rec} />

          <section>
            <div className="sec-label">Vrednovanje — što kaže svaka metoda</div>
            <p className="spread-lead">
              {data.valuation.reconciliation && data.valuation.reconciliation.divergent
                ? 'Metode se ne slažu — i taj raskorak je poanta.'
                : 'Usporedba metoda vrednovanja.'}
            </p>
            <p className="spread-note">
              Svaka metoda daje raspon (€/dionici) uz navedenu pouzdanost.
              Okomite linije su zadnje tržišne cijene klasa. Zelena traka je zona između
              najniže i najviše središnje procjene.
            </p>
            <VerdictSpread
              methods={data.valuation.ran}
              classes={data.share_classes}
              reconciliation={data.valuation.reconciliation}
              liquidity={data.liquidity}
            />
            <div className="srcnote">
              Pouzdanost po metodi:{' '}
              {data.valuation.ran.map((m, i) => (
                <React.Fragment key={m.key}>
                  {i > 0 && ' · '}
                  {m.label} <b>{num(m.confidence, 1)}</b>
                </React.Fragment>
              ))}
            </div>
          </section>

          <div className="cols">
            <section className="narr">
              <div className="sec-label">Zašto se metode razilaze</div>
              <Narrative data={data} />
            </section>
            <SotpTable sotp={data.valuation.sotp} />
          </div>

          <section>
            <div className="sec-label">Metode koje se ne primjenjuju</div>
            {data.valuation.skipped.map((s) => (
              <div className="skip" key={s.key}>
                <span className="m">{s.label}</span>
                <span>{s.reason}</span>
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
            <b>Informativno, nije investicijski savjet ni preporuka.</b>{' '}
            {data.mar_note} Stavke označene <span className="flag">pretpostavka</span> /{' '}
            <span className="ph">pretp.</span> nisu potvrđene iz izvora. Cijene su službeni
            EOD zaključci Zagrebačke burze, s odmakom. Podaci koji nedostaju u bazi prikazani
            su prazni — ništa se ne procjenjuje na stranici.
          </div>
        </>
        )
      })()}
      </main>
      <SiteFooter />
    </div>
  )
}
