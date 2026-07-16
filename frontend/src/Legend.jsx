import React from 'react'

/* Legenda pojmova — jedna rečenica OBIČNIM jezikom po pojmu (dizajn:
   dvorazinski princip — jednostavno vidljivo, tehnički detalj iza klika).
   TERMS koristi i <Term> tooltip; tekst je edukativan, bez ocjena (MAR). */

export const TERMS = {
  'P/E': 'Cijena dionice podijeljena godišnjom zaradom po dionici — koliko godina zarade plaćate po današnjoj cijeni.',
  'P/B': 'Cijena dionice podijeljena knjigovodstvenom vrijednošću po dionici — koliko plaćate po euru vlastitog kapitala firme.',
  'EV/EBITDA': 'Vrijednost cijelog poslovanja (s dugom) podijeljena operativnom zaradom — omjer neovisan o načinu financiranja.',
  DCF: 'Diskontirani novčani tok — budući slobodni novac firme preračunat na današnju vrijednost.',
  comps: 'Peer usporedba — jedna metoda koja kroz više leća (P/E, EV/EBITDA, EV/EBIT, P/B) uspoređuje firmu sa sličnima; leće su ulazi, ne zasebne metode.',
  SOTP: 'Zbroj dijelova (sum-of-the-parts) — holding se vrednuje tako da se zbroje vrijednosti svih tvrtki koje drži, minus dug.',
  DDM: 'Dividendni model — vrijednost dionice kao zbroj svih budućih dividendi preračunatih na danas.',
  ROE: 'Povrat na kapital — koliko firma godišnje zaradi na svakih 100 € vlastitog kapitala.',
  EBITDA: 'Operativna zarada prije kamata, poreza i amortizacije — gruba mjera koliko posao stvara novca.',
  backlog: 'Ugovoreni, još neisporučeni poslovi — narudžbe koje čekaju izvršenje i daju uvid u buduće prihode.',
  'fer-zona': 'Naša procjena vrijednosti dionice. Cijena iznad zone znači da tržište plaća više nego što fundamenti govore; ispod — obrnuto. Zaključak je vaš.',
  sidro: 'Glavna metoda procjene za tip firme (holding → SOTP, banka → kapital, industrija → DCF); ostale metode služe kao kontrola.',
  beta: 'Koliko dionica njiše u odnosu na tržište: 1 = kao tržište, više = jače njihanje (rizičnije), manje = mirnije.',
  'trošak kapitala': 'Prinos koji ulagač razumno traži za rizik ove dionice; veći trošak = stroža (niža) procjena vrijednosti. Oznaka: r.',
  r: 'Trošak kapitala — prinos koji ulagač razumno traži za rizik ove dionice. Slaže se kao zbroj: rf + β×ERP + CRP (+ premija nelikvidnosti). Veći r = stroža (niža) procjena.',
  rf: 'Bezrizični prinos — prinos "bez rizika" u euru (10-godišnja njemačka državna obveznica, Bund). Temelj od kojeg svaki traženi prinos kreće; rizik Hrvatske NIJE ovdje nego u CRP-u.',
  ERP: 'Premija rizika tržišta dionica (equity risk premium) — koliko ulagači povrh bezrizičnog prinosa traže za ulaganje u dionice općenito (zrelo tržište, bez premije zemlje). Množi se betom dionice.',
  CRP: 'Premija rizika zemlje (country risk premium) — mali dodatak na traženi prinos zbog ulaganja u Hrvatsku; primjeren investment-grade eurozoni i računa se točno jednom (nije skriven ni u rf-u ni u ERP-u).',
  TTM: 'Zadnjih 12 mjeseci (trailing twelve months) — zarada/prihodi zbrojeni kroz posljednja četiri kvartala umjesto iz zadnjeg godišnjeg izvješća; svježija slika poslovanja.',
  g: 'Stopa rasta — koliko firma (ili njezina dividenda) raste godišnje. Trajni g je rast "zauvijek" i drži se konzervativno: 2,5% za kapitalne metode, 4% terminalno za DCF/DDM.',
  g1: 'Stopa rasta eksplicitne faze (prvih 5 godina) — kompozit (medijan) tri signala iz objavljenih brojki: višegodišnja serija, održivi rast iz zadržane dobiti (ROE × neisplaćeni dio dobiti) i konzervativno terminalno sidro; ograničen odozgo (10% sa serijom, 8% bez) i uvijek ispod troška kapitala r, zatim postupno pada prema trajnom g.',
  CAGR: 'Prosječna godišnja stopa rasta kroz više godina (compound annual growth rate) — npr. "3g CAGR prihoda" je prosječni godišnji rast prihoda u zadnje tri godine.',
  payout: 'Udio dobiti koji firma isplati kao dividendu — npr. payout 60% znači da od svakih 100 € dobiti dioničarima ode 60 €.',
  D_sust: 'Naša procjena ODRŽIVE godišnje dividende po dionici: održivi payout (medijan povijesnih payouta, samo redovne isplate — jednokratne ne ulaze; kod banaka najviše 70%) × dobit zadnjih 12 mjeseci ÷ broj dionica.',
  'dividendni pod': 'Donja granica vrijednosti iz održive dividende (Gordonov izračun: D_sust ÷ (r − g)) — kad bi zona pala ispod nje, sama dividenda bi nosila više nego što ulagač traži za rizik, pa se pod uključuje u zonu.',
  medijan: 'Srednja vrijednost po redoslijedu — pola vrijednosti je iznad, pola ispod; otporniji na ekstremne vrijednosti od običnog prosjeka.',
}

/* Pojam s tooltipom — točkasto podcrtan; definicija na hover (title). */
export function Term({ t, children }) {
  const def = TERMS[t]
  if (!def) return children ?? t
  return <span className="term" title={def}>{children ?? t}</span>
}

export function Legend({ open = false }) {
  return (
    <details className="legend" open={open}>
      <summary>LEGENDA POJMOVA — što znače kratice i termini (klik za otvaranje)</summary>
      <dl>
        {Object.entries(TERMS).map(([k, v]) => (
          <div className="legend-row" key={k} id={`legenda-${k.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <div className="legend-note">
        Objašnjenja su edukativna i pojednostavljena; točne formule i izvori stoje
        uz svaku metodu i pretpostavku na stranici.
      </div>
    </details>
  )
}
