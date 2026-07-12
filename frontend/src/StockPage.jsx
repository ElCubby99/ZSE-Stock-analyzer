import React, { useEffect, useState } from 'react'
import { NavLink, useParams } from 'react-router-dom'
import VerdictSpread from './VerdictSpread.jsx'
import {
  AnalysisUnavailable, Dividends, IlliquidBanner, PriceChart, ProfileHeader,
  SectionRule, StatsStrip,
} from './MarketProfile.jsx'
import { dash, eur, meur, num, pct } from './format.js'

// live firme (orchestrator) + CROS/ZABA (M1–M5) + HPB/HT (samo tržišni profil)
const TICKERS = ['ADRS', 'CROS', 'ZABA', 'ADPL', 'ARNT', 'ATGR', 'DLKV', 'HPB',
  'HT', 'IG', 'KODT', 'KOEI', 'PODR', 'RIVP', 'SPAN', 'TOK', 'ZITO']

const SECTOR_HR = {
  holding: 'Holding', insurance: 'Osiguranje', tourism: 'Turizam',
  consumer: 'Konzumeri', industrial: 'Industrija', bank: 'Banka',
  telecom: 'Telekomunikacije', technology: 'Tehnologija', energy: 'Energetika',
  shipping: 'Brodarstvo', aquaculture: 'Marikultura',
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

/* ---------- v2 sekcije ---------- */

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

function Ownership({ own, liquidity }) {
  if (!own) return null
  const anyFlag = (liquidity?.classes || []).some((c) => c.flag !== 'ok')
  return (
    <section>
      <div className="sec-label">Vlasništvo i free float</div>
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
      ) : (
        <div className="subnote"><span className="flag">nema u bazi</span> {own.note}.</div>
      )}
    </section>
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

function Assumptions({ valuation }) {
  const p = valuation.params
  const cards = [
    { name: 'Trošak kapitala r', out: pct(p.r, 2), src: p.sources.r, sure: p.rates_calibrated },
    { name: 'Perpetualni rast g', out: pct(p.g, 1), src: p.sources.g, sure: p.rates_calibrated },
  ]
  if (valuation.sotp) {
    cards.push({
      name: 'Holding diskont',
      out: `${num(p.holding_discount_low * 100, 0)}–${num(p.holding_discount_high * 100, 0)}%`,
      src: p.sources.holding_discount, sure: false,
    })
  }
  cards.push({
    name: 'Peer multipli (P/E · P/B)',
    out: `${num(p.peer_pe, 2)} · ${num(p.peer_pb, 2)}`,
    src: p.sources.peers, sure: p.peers_calibrated,
  })
  return (
    <section>
      <div className="sec-label">Pretpostavke — vrijednosti s izvorom (samo za čitanje)</div>
      <div className="controls">
        {cards.map((c) => (
          <div className="ctrl" key={c.name}>
            <div className="top">
              <span className="name">
                {c.name}{' '}
                {c.sure ? <span className="okflag">izvor</span> : <span className="flag">pretpostavka</span>}
              </span>
              <span className="out mono">{c.out}</span>
            </div>
            <div className="src">{c.src || 'izvor nije zabilježen'}</div>
          </div>
        ))}
      </div>
      <ul className="flaglist">
        {valuation.assumption_flags.map((f) => (
          <li key={f.key}>
            <span className="flag">pretpostavka</span> {f.label} — {f.why}
          </li>
        ))}
      </ul>
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
        Raspon središnjih procjena je {eur(rec.zone_low, 0)}–{eur(rec.zone_high, 0)} uz
        disperziju od {num(rec.dispersion * 100, 0)}%
        {rec.divergent
          ? ' — metode se snažno razilaze, pa je sam raskorak informacija: svaka leća mjeri drugo svojstvo.'
          : ' — metode su relativno usklađene.'}
      </p>
      <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
        Koja je leća mjerodavna ovisi o tome što društvo jest (operativna firma, holding, osiguratelj);
        procjenu prepuštamo čitatelju. Pretpostavke i izvori svake metode navedeni su iznad.
      </p>
    </>
  )
}

function SotpTable({ sotp }) {
  if (!sotp) return null
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
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

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
    if (data) document.title = `${data.ticker} — ${data.name} · analiza`
  }, [data])

  return (
    <div className="wrap">
      <nav className="topnav">
        <span className="brand">ZSE analiza</span>
        {TICKERS.map((t) => (
          <NavLink key={t} to={`/dionica/${t}`} className={({ isActive }) => (isActive ? 'active' : '')}>
            {t}
          </NavLink>
        ))}
      </nav>

      {err && <section className="error">Greška: {err}</section>}
      {!data && !err && <div className="loading">učitavam {ticker}…</div>}

      {data && (() => {
        const marketOnly = data.data_status === 'market_only'
        const rec = data.valuation?.reconciliation
        const zone = rec && rec.zone_low !== null && rec.zone_high !== null
          ? [rec.zone_low, rec.zone_high] : null
        return (
        <>
          {/* ============ GORE · TRŽIŠNI PROFIL ============ */}
          <ProfileHeader data={{ ...data, sector_hr: SECTOR_HR[data.sector] || data.sector }}
            zone={zone} />
          <IlliquidBanner liquidity={data.liquidity} />
          <SectionRule n="01" title="Tržišni podaci" />
          <PriceChart data={data} zone={zone} />
          <StatsStrip data={data} />
          <Dividends data={data} />

          {/* ============ DOLJE · POSTOJEĆA ANALIZA ============ */}
          <SectionRule n="02" title="Analiza vrijednosti" />
          {marketOnly ? (
            <AnalysisUnavailable note={data.data_note} />
          ) : (
          <>
          <Metrics data={data} />
          <Assumptions valuation={data.valuation} />

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

          <Fin3Y f3={data.financials_3y} />
          <Balance b={data.balance} />
          <BankKpi bk={data.bank_kpi} />
          <Segments seg={data.segments} />
          <Ownership own={data.ownership} liquidity={data.liquidity} />

          <section>
            <div className="sec-label">Metode koje se ne primjenjuju</div>
            {data.valuation.skipped.map((s) => (
              <div className="skip" key={s.key}>
                <span className="m">{s.label}</span>
                <span>{s.reason}</span>
              </div>
            ))}
          </section>

          <Fundamentals data={data} />
          </>
          )}

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
    </div>
  )
}
