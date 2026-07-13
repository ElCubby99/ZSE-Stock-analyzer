import React from 'react'

/* Legenda pojmova — jedna rečenica OBIČNIM jezikom po pojmu (dizajn:
   dvorazinski princip — jednostavno vidljivo, tehnički detalj iza klika).
   TERMS koristi i <Term> tooltip; tekst je edukativan, bez ocjena (MAR). */

export const TERMS = {
  'P/E': 'Cijena dionice podijeljena godišnjom zaradom po dionici — koliko godina zarade plaćate po današnjoj cijeni.',
  'P/B': 'Cijena dionice podijeljena knjigovodstvenom vrijednošću po dionici — koliko plaćate po euru vlastitog kapitala firme.',
  'EV/EBITDA': 'Vrijednost cijelog poslovanja (s dugom) podijeljena operativnom zaradom — omjer neovisan o načinu financiranja.',
  DCF: 'Diskontirani novčani tok — budući slobodni novac firme preračunat na današnju vrijednost.',
  SOTP: 'Zbroj dijelova (sum-of-the-parts) — holding se vrednuje tako da se zbroje vrijednosti svih tvrtki koje drži, minus dug.',
  DDM: 'Dividendni model — vrijednost dionice kao zbroj svih budućih dividendi preračunatih na danas.',
  ROE: 'Povrat na kapital — koliko firma godišnje zaradi na svakih 100 € vlastitog kapitala.',
  EBITDA: 'Operativna zarada prije kamata, poreza i amortizacije — gruba mjera koliko posao stvara novca.',
  backlog: 'Ugovoreni, još neisporučeni poslovi — narudžbe koje čekaju izvršenje i daju uvid u buduće prihode.',
  'fer-zona': 'Naša procjena vrijednosti dionice. Cijena iznad zone znači da tržište plaća više nego što fundamenti govore; ispod — obrnuto. Zaključak je vaš.',
  sidro: 'Glavna metoda procjene za tip firme (holding → SOTP, banka → kapital, industrija → DCF); ostale metode služe kao kontrola.',
  beta: 'Koliko dionica njiše u odnosu na tržište: 1 = kao tržište, više = jače njihanje (rizičnije), manje = mirnije.',
  'trošak kapitala': 'Prinos koji ulagač razumno traži za rizik ove dionice; veći trošak = stroža (niža) procjena vrijednosti.',
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
