import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'

/* Impressum (M21): diskretna ali potpuna stranica za informativni servis.
   Jedini kontakt: info@burzovnilist.com (bez telefona/adrese/imena osobe). */

/* Content je čist (bez hookova) — koristi ga SPA wrapper i prerender (SSR). */
export function ImpressumContent() {
  return (
    <>

        <section>
          <div className="sec-label">O servisu</div>
          <p className="imp-p"><b>Burzovni list</b> — analitička platforma za
          dionice uvrštene na Zagrebačku burzu. Servis je informativan i
          edukativan; nije investicijsko društvo, ne pruža investicijsko
          savjetovanje i ne posreduje u trgovanju.</p>
          <p className="imp-p">Kontakt: <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a></p>
        </section>

        <section>
          <div className="sec-label">Informativni karakter (MAR)</div>
          <p className="imp-p">Prikazani podaci, rasponi i fer-zone su
          informativni i analitički — ne predstavljaju investicijski savjet,
          preporuku ni poticaj na kupnju ili prodaju financijskih instrumenata.
          Servis ne objavljuje ciljne cijene, rejtinge ni preporuke; položaj
          tržišne cijene naspram fer-zone je činjenični prikaz uz javno
          ispisane pretpostavke, a zaključak je uvijek čitateljev. Svaka
          brojka na stranicama nosi izvor (dokument i stranicu s koje je
          preuzeta); gdje podatak nije dostupan ili primjenjiv, piše n/p —
          vrijednosti se ne izmišljaju.</p>
        </section>

        <section>
          <div className="sec-label">Automatizacija i nadzor</div>
          <p className="imp-p">Analize i procjene na ovom servisu generira
          automatizirani sustav uz ljudski nadzor. Metode, pravila, parametri
          i priznate greške sustava javno su opisani na stranici{' '}
          <Link to="/metodologija">Metodologija</Link>, uključujući povijest
          promjena svake procjene.</p>
        </section>

        <section>
          <div className="sec-label">Podaci</div>
          <p className="imp-p">Tržišni podaci: službena EOD tečajnica
          Zagrebačke burze (zse.hr); objavljuje se nakon zatvaranja trgovine,
          a uz svaku cijenu stoji stvarni datum podatka.
          Financijski podaci: javno objavljena izvješća izdavatelja
          (EHO/ZSE). Vrijednosti rijetko trgovanih dionica su indikativne i
          tako su označene. Unatoč pažnji pri obradi, servis ne jamči potpunu
          točnost ni pravodobnost podataka — mjerodavni su izvorni dokumenti
          izdavatelja i službene objave burze.</p>
        </section>

        <div className="disc">
          Korištenjem servisa prihvaćate da se sadržaj koristi isključivo u
          informativne svrhe. Za investicijske, porezne ili pravne odluke
          potražite ovlaštenog savjetnika.
        </div>
    </>
  )
}

export default function Impressum() {
  useEffect(() => { document.title = 'Impressum · Burzovni list' }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">Impressum</h1>
        <ImpressumContent />
      </main>
      <SiteFooter />
    </div>
  )
}
