import React, { useEffect, useMemo, useState } from 'react'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { num } from './format.js'

/* Alati (dizajn B): SVE klijentski — računa isključivo IZ KORISNIKOVA UNOSA,
   bez backend poziva i bez podataka o konkretnim dionicama. MAR: alati ne
   predlažu ni alokaciju ni vrijednosnice; disclaimer po kartici. */

const DISC = 'Izračun iz vaših unosa — nije investicijski ni porezni savjet.'

function Num({ label, v, set, step = 1, min = 0, suffix = '' }) {
  return (
    <label className="tool-in">
      <span>{label}</span>
      <span className="tool-in-f">
        <input type="number" value={v} step={step} min={min}
          onChange={(e) => set(parseFloat(e.target.value) || 0)} />{suffix}
      </span>
    </label>
  )
}

function Card({ title, children, extra }) {
  return (
    <section className="tool-card">
      <div className="sec-label">{title}</div>
      {children}
      <div className="subnote">{extra || DISC}</div>
    </section>
  )
}

function Out({ label, v, strong }) {
  return (
    <div className="tool-out">
      <span>{label}</span>
      <b className={strong ? 'pine' : ''}>{v}</b>
    </div>
  )
}

const eur0 = (v) => `${num(v, 0)} €`

function Dividendni() {
  const [kom, setKom] = useState(100); const [dps, setDps] = useState(1.0)
  const [cij, setCij] = useState(20)
  return (
    <Card title="1 · Dividendni kalkulator">
      <Num label="Broj dionica" v={kom} set={setKom} />
      <Num label="Dividenda po dionici (€)" v={dps} set={setDps} step={0.01} />
      <Num label="Vaša prosječna cijena (€)" v={cij} set={setCij} step={0.01} />
      <Out label="Godišnja dividenda (bruto, prije poreza)" v={eur0(kom * dps)} strong />
      <Out label="Prinos na vaš trošak" v={cij > 0 ? `${num((dps / cij) * 100, 2)} %` : '—'} />
    </Card>
  )
}

function Prinos() {
  const [p0, setP0] = useState(1000); const [p1, setP1] = useState(1300)
  const [god, setGod] = useState(3)
  const tot = p0 > 0 ? p1 / p0 - 1 : null
  const cagr = p0 > 0 && p1 > 0 && god > 0 ? (p1 / p0) ** (1 / god) - 1 : null
  return (
    <Card title="2 · Kalkulator prinosa">
      <Num label="Početna vrijednost (€)" v={p0} set={setP0} />
      <Num label="Konačna vrijednost (€)" v={p1} set={setP1} />
      <Num label="Razdoblje (godine)" v={god} set={setGod} step={0.5} />
      <Out label="Ukupni prinos" v={tot === null ? '—' : `${num(tot * 100, 1)} %`} />
      <Out label="Godišnji (CAGR)" v={cagr === null ? '—' : `${num(cagr * 100, 2)} %`} strong />
    </Card>
  )
}

function DcfDdm() {
  const [d, setD] = useState(1.0); const [f, setF] = useState(2.0)
  const [r, setR] = useState(9); const [g, setG] = useState(2.5)
  const ok = r / 100 > g / 100
  const gordon = ok ? (d * (1 + g / 100)) / (r / 100 - g / 100) : null
  const dcf = ok ? (f * (1 + g / 100)) / (r / 100 - g / 100) : null
  return (
    <Card title="3 · DCF / DDM (Gordon)"
      extra={`${DISC} r i g su VAŠE pretpostavke; default g=2,5% je pretpostavka platforme (nominalni BDP proxy), ne prognoza.`}>
      <Num label="Dividenda po dionici (€)" v={d} set={setD} step={0.05} />
      <Num label="FCF po dionici (€)" v={f} set={setF} step={0.05} />
      <Num label="Trošak kapitala r (%)" v={r} set={setR} step={0.1} />
      <Num label="Perpetualni rast g (%)" v={g} set={setG} step={0.1} />
      {!ok && <div className="prof-empty-box">g mora biti manji od r (perpetuitet inače nema smisla).</div>}
      <Out label="DDM vrijednost (D×(1+g)/(r−g))" v={gordon === null ? '—' : `${num(gordon, 2)} €`} strong />
      <Out label="DCF perpetuitet (FCF×(1+g)/(r−g))" v={dcf === null ? '—' : `${num(dcf, 2)} €`} />
    </Card>
  )
}

function Porez() {
  const [pr, setPr] = useState(1500); const [tr, setTr] = useState(1000)
  const [drz, setDrz] = useState(1.0)
  const dobit = pr - tr
  const oslobodjen = drz >= 2
  const porez = oslobodjen || dobit <= 0 ? 0 : dobit * 0.12
  return (
    <Card title="4 · Porez na kapitalni dobitak (HR)"
      extra={'Pravila (provjereno 14.07.2026., Porezna uprava — "Dohodak od kapitala po osnovi kapitalnih dobitaka" i "Oporezivanje kapitalnih dobitaka i izvješćivanje putem Obrasca JOPPD", porezna-uprava.gov.hr): stopa 12% na NETO dobitke (dobitci − gubitci iste godine) ako je imovina otuđena unutar 2 godine od stjecanja; nakon 2 godine držanja dobitak nije oporeziv i ne prijavljuje se; obračun, obustava i uplata (Obrazac JOPPD) do posljednjeg dana veljače za prethodnu godinu. NIJE porezni savjet — provjerite s poreznim savjetnikom.'}>
      <Num label="Prodajna vrijednost (€)" v={pr} set={setPr} />
      <Num label="Trošak stjecanja (€)" v={tr} set={setTr} />
      <Num label="Držanje (godine)" v={drz} set={setDrz} step={0.1} />
      <Out label="Kapitalni dobitak" v={eur0(dobit)} />
      <Out label="Porez (12%)" v={oslobodjen ? 'oslobođeno (>2 g držanja)' : dobit <= 0 ? '0 € (gubitak — netira se s dobicima iste godine)' : eur0(porez)} strong />
      <Out label="Neto" v={eur0(pr - porez)} />
    </Card>
  )
}

function Kamatni() {
  const [gl, setGl] = useState(1000); const [mj, setMj] = useState(100)
  const [st, setSt] = useState(5); const [god, setGod] = useState(10)
  const res = useMemo(() => {
    const rm = st / 100 / 12; let v = gl; let uplate = gl
    for (let i = 0; i < god * 12; i++) { v = v * (1 + rm) + mj; uplate += mj }
    return { v, uplate }
  }, [gl, mj, st, god])
  return (
    <Card title="5 · Složeni kamatni račun">
      <Num label="Početna glavnica (€)" v={gl} set={setGl} />
      <Num label="Mjesečna uplata (€)" v={mj} set={setMj} />
      <Num label="Godišnja stopa (%)" v={st} set={setSt} step={0.1} />
      <Num label="Godine" v={god} set={setGod} />
      <Out label="Ukupno uplaćeno" v={eur0(res.uplate)} />
      <Out label="Vrijednost na kraju" v={eur0(res.v)} strong />
      <Out label="Od toga kamata/prinos" v={eur0(res.v - res.uplate)} />
    </Card>
  )
}

/* 6 · GLAVNI: rast imovine po klasama — alokacija + POMIČNE pretpostavke prinosa */
const KLASE = [
  { k: 'nekretnine', l: 'Nekretnine', a: 30, r: 4 },
  { k: 'dionice', l: 'Dionice', a: 30, r: 6 },
  { k: 'obveznice', l: 'Obveznice', a: 20, r: 3 },
  { k: 'zlato', l: 'Zlato', a: 10, r: 3 },
  { k: 'gotovina', l: 'Gotovina', a: 10, r: 1 },
]
const KCOL = { nekretnine: '#7A6234', dionice: '#9E2B25', obveznice: '#2F5D86',
  zlato: '#8A6D1F', gotovina: '#4A555E' }

function RastImovine() {
  const [iznos, setIznos] = useState(10000)
  const [god, setGod] = useState(10)
  const [alok, setAlok] = useState(Object.fromEntries(KLASE.map((k) => [k.k, k.a])))
  const [ret, setRet] = useState(Object.fromEntries(KLASE.map((k) => [k.k, k.r])))
  const sumA = KLASE.reduce((s, k) => s + alok[k.k], 0)
  const proj = useMemo(() => {
    const per = KLASE.map((k) => {
      const start = iznos * (alok[k.k] / 100)
      const grow = (dr) => start * (1 + (ret[k.k] + dr) / 100) ** god
      return { ...k, start, end: grow(0), lo: grow(-2), hi: grow(+2) }
    })
    const tot = (f) => per.reduce((s, p) => s + p[f], 0)
    return { per, end: tot('end'), lo: tot('lo'), hi: tot('hi') }
  }, [iznos, god, alok, ret])
  return (
    <section className="tool-card tool-wide">
      <div className="sec-label">6 · Rast imovine po klasama — "što ako" projekcija</div>
      <div className="tool-2col">
        <div>
          <Num label="Iznos (€)" v={iznos} set={setIznos} step={100} />
          <Num label="Razdoblje (godine)" v={god} set={setGod} />
          <div className="bp-h">Alokacija (%) — zbroj mora biti 100</div>
          {KLASE.map((k) => (
            <label className="tool-slider" key={k.k}>
              <span><i style={{ background: KCOL[k.k] }} /> {k.l}</span>
              <input type="range" min="0" max="100" value={alok[k.k]}
                onChange={(e) => setAlok({ ...alok, [k.k]: +e.target.value })} />
              <b>{alok[k.k]} %</b>
            </label>
          ))}
          <div className={`tool-sum ${sumA === 100 ? '' : 'warn'}`}>
            Σ alokacija: {sumA} % {sumA !== 100 && '— podesite na 100 % za smislenu projekciju'}
          </div>
          <div className="bp-h">Pretpostavljeni godišnji prinos po klasi (%)</div>
          <div className="subnote" style={{ marginTop: 0 }}>
            VAŠE pretpostavke, ne prognoza platforme — pomičite po vlastitoj procjeni.
          </div>
          {KLASE.map((k) => (
            <label className="tool-slider" key={k.k}>
              <span><i style={{ background: KCOL[k.k] }} /> {k.l}</span>
              <input type="range" min="-5" max="15" step="0.5" value={ret[k.k]}
                onChange={(e) => setRet({ ...ret, [k.k]: +e.target.value })} />
              <b>{num(ret[k.k], 1)} %</b>
            </label>
          ))}
        </div>
        <div>
          <Out label={`Projekcija nakon ${god} g (uz vaše pretpostavke)`} v={eur0(proj.end)} strong />
          <Out label="Raspon ishoda (svi prinosi ∓2 p.b.)" v={`${eur0(proj.lo)} – ${eur0(proj.hi)}`} />
          <div className="bp-h">Doprinos po klasi na kraju razdoblja</div>
          <div className="alloc-bar">
            {proj.per.filter((p) => p.end > 0).map((p) => (
              <div key={p.k} style={{ width: `${(p.end / proj.end) * 100}%`, background: KCOL[p.k] }} />
            ))}
          </div>
          {proj.per.map((p) => (
            <div className="tool-out small" key={p.k}>
              <span><i className="sw" style={{ background: KCOL[p.k] }} /> {p.l}</span>
              <b>{eur0(p.end)} <em>({eur0(p.lo)}–{eur0(p.hi)})</em></b>
            </div>
          ))}
        </div>
      </div>
      <div className="subnote">
        Projekcija se računa isključivo iz vaših unosa i pretpostavki; alat NE
        predlaže alokaciju. Pretpostavljeni prinosi nisu jamstvo — stvarni
        prinosi mogu biti i negativni, a raspon ∓2 p.b. je ilustracija
        osjetljivosti, ne granica mogućih ishoda. Nije investicijski savjet.
      </div>
    </section>
  )
}

export default function Alati() {
  useEffect(() => { document.title = 'Alati · ZSE analiza' }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
      <h1 className="page-h1">Alati</h1>
      <p className="risk-sub">kalkulatori računaju isključivo iz vaših unosa — bez podataka o konkretnim dionicama i bez preporuka</p>
      <RastImovine />
      <div className="tool-grid">
        <Dividendni />
        <Prinos />
        <DcfDdm />
        <Porez />
        <Kamatni />
      </div>
      <div className="disc">
        Svi izračuni su informativni i temelje se na unosima korisnika. Ništa na
        ovoj stranici nije investicijski, porezni ni pravni savjet.
      </div>
      </main>
      <SiteFooter />
    </div>
  )
}
