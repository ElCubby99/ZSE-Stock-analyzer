import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { CONSENT_VERSION, useConsent } from './consent.jsx'

/* M24: tri pravne stranice — Politika kolačića, Uvjeti korištenja,
   Politika privatnosti. Isti layout kao Impressum. Dostupne bez prijave i
   bez pristanka na kolačiće. Tablica kolačića odražava STVARNO stanje
   (bl_consent, sb-* auth, lastTicker; analitika još nije uvedena). */

const UPDATED = '15.07.2026.'

function LegalPage({ title, children }) {
  useEffect(() => { document.title = `${title} · Burzovni list` }, [title])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">{title}</h1>
        {children}
      </main>
      <SiteFooter />
    </div>
  )
}

/* ============================ /politika-kolacica ============================ */

const COOKIES = [
  {
    name: 'bl_consent',
    purpose: 'pamti vaš izbor o kolačićima (verzija politike, datum, odabrane kategorije)',
    cat: 'nužni', dur: '12 mjeseci', party: 'prva strana (localStorage)',
  },
  {
    name: 'sb-<projekt>-auth-token',
    purpose: 'sesija prijavljenog korisnika (Supabase Auth) — postoji samo ako se prijavite',
    cat: 'nužni', dur: 'do odjave / isteka sesije', party: 'prva strana (localStorage)',
  },
  {
    name: 'lastTicker',
    purpose: 'pamti zadnju otvorenu dionicu radi navigacijske prečice u zaglavlju',
    cat: 'nužni (funkcionalni)', dur: 'do brisanja iz preglednika', party: 'prva strana (localStorage)',
  },
  {
    name: '_ga',
    purpose: 'Google analitika (učitava se kroz Google Tag Manager) — razlikovanje posjetitelja; postavlja se SAMO ako pristanete na analitičke kolačiće',
    cat: 'analitički', dur: 'do 2 godine', party: 'treća strana (Google)',
  },
  {
    name: '_ga_*',
    purpose: 'Google analitika — stanje sesije po mjernom svojstvu; postavlja se SAMO ako pristanete na analitičke kolačiće',
    cat: 'analitički', dur: 'do 2 godine', party: 'treća strana (Google)',
  },
]

export function PolitikaKolacica() {
  const { openSettings } = useConsent()
  return (
    <LegalPage title="Politika kolačića">
      <section>
        <div className="sec-label">Što su kolačići i tko ih postavlja</div>
        <p className="imp-p">Kolačići (cookies) i srodne tehnologije lokalne
        pohrane (localStorage) male su količine podataka koje preglednik čuva
        na vašem uređaju. Postavlja ih <b>Burzovni list</b> kao operator ove
        stranice. Ovaj servis trenutno koristi isključivo pohranu prve strane
        navedenu u tablici — tehnički kroz localStorage preglednika, na koju
        se primjenjuju ista pravila privole kao na kolačiće (pohrana na
        uređaju korisnika).</p>
      </section>

      <section>
        <div className="sec-label">Tablica kolačića i lokalne pohrane</div>
        <table>
          <thead><tr><th>Naziv</th><th>Svrha</th><th>Kategorija</th>
            <th>Trajanje</th><th>Prva/treća strana</th></tr></thead>
          <tbody>
            {COOKIES.map((c) => (
              <tr key={c.name}>
                <td><code>{c.name}</code></td>
                <td>{c.purpose}</td>
                <td>{c.cat}</td>
                <td>{c.dur}</td>
                <td className="fund-src">{c.party}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="imp-p" style={{ marginTop: 10 }}>
          <b>Analitika (Google Tag Manager uz Google Consent Mode v2)</b>:
          prije vašeg pristanka svi su načini pohrane postavljeni na
          „denied" — analitički kolačići se NE postavljaju. Tek pristankom na
          kategoriju „Analitički" pohrana prelazi u „granted" i kolačići iz
          tablice se postavljaju. Povučete li pristanak, pohrana se odmah
          vraća na „denied", a postojeći <code>_ga</code>/<code>_ga_*</code>{' '}
          kolačići se brišu. Marketinške kolačiće ne koristimo.
        </p>
      </section>

      <section>
        <div className="sec-label">Kako upravljati pristankom</div>
        <p className="imp-p">Svoj izbor možete promijeniti ili povući u svakom
        trenutku — jednako lako kao što je dan:{' '}
        <button type="button" className="cc-inline-link" onClick={openSettings}>
          otvori postavke kolačića
        </button>{' '}
        (ista poveznica stoji trajno u podnožju svake stranice). Kolačiće i
        lokalnu pohranu možete obrisati i u pregledniku: Postavke →
        Privatnost → Kolačići i podaci stranica (Chrome/Edge), odnosno
        Postavke → Privatnost i sigurnost (Firefox). Odbijanje ne-nužnih
        kolačića ne ograničava korištenje stranice.</p>
      </section>

      <section>
        <div className="sec-label">Pravna osnova</div>
        <p className="imp-p">Nužni kolačići i pohrana: nužnost pružanja usluge
        koju ste zatražili i legitimni interes operatora (čl. 6. st. 1. t. (b)
        i (f) GDPR-a; čl. 5. st. 3. ePrivacy direktive — iznimka za strogo
        nužnu pohranu). Analitički i marketinški kolačići: isključivo vaša
        privola (čl. 6. st. 1. t. (a) GDPR-a), koju možete povući u svakom
        trenutku bez posljedica za korištenje stranice.</p>
      </section>

      <section>
        <div className="sec-label">Verzija i izmjene</div>
        <p className="imp-p">Verzija politike: <b>{CONSENT_VERSION}</b> ·
        zadnja izmjena: <b>{UPDATED}</b> Promijeni li se politika, zapis vašeg
        pristanka prestaje vrijediti i pri sljedećem posjetu ponovno ćemo vas
        pitati. Pristanak u svakom slučaju vrijedi najviše 12 mjeseci.</p>
        <p className="imp-p">Više o obradi osobnih podataka:{' '}
        <Link to="/politika-privatnosti">Politika privatnosti</Link>.</p>
      </section>
    </LegalPage>
  )
}

/* ============================ /uvjeti-koristenja ============================ */

export function UvjetiKoristenja() {
  return (
    <LegalPage title="Uvjeti korištenja">
      <section>
        <div className="sec-label">1. Opće odredbe</div>
        <p className="imp-p">Ove Uvjete korištenja primjenjuje <b>Burzovni
        list</b> (dalje: „operator"), pružatelj informativnog servisa na
        adresi burzovnilist.com — platforme za informativni prikaz podataka i
        analitičkih raspona za dionice uvrštene na Zagrebačku burzu. Podaci o
        operatoru i kontakt navedeni su u <Link to="/impressum">Impressumu</Link>{' '}
        (<a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a>).
        Korištenjem stranice prihvaćate ove Uvjete.</p>
      </section>

      <section>
        <div className="sec-label">2. Informativna priroda sadržaja</div>
        <p className="imp-p">Prikazani podaci, rasponi i fer-zone su
        informativni i analitički — ne predstavljaju investicijski savjet,
        preporuku ni poziv na kupnju ili prodaju financijskih instrumenata.
        Fer-zone i rasponi rezultat su javno opisane{' '}
        <Link to="/metodologija">metodologije</Link> s pretpostavkama koje su
        ispisane uz svaku analizu; zaključak je uvijek čitateljev. Vrijednosti
        ilikvidnih dionica su indikativne i tako su označene. Servis ne
        objavljuje ciljne cijene, rejtinge ni preporuke.</p>
      </section>

      <section>
        <div className="sec-label">3. Izvori podataka i točnost</div>
        <p className="imp-p">Podaci se temelje na službenim EOD zaključcima
        Zagrebačke burze (objavljuju se nakon zatvaranja trgovine; mogući je
        odmak, a uz svaku cijenu stoji stvarni datum podatka) i javno
        objavljenim izvješćima izdavatelja (EHO/ZSE). Operator ne jamči
        potpunost, točnost ni ažurnost podataka; podaci koji nedostaju
        prikazuju se prazni (n/p) i ne procjenjuju se. Mjerodavni su izvorni
        dokumenti izdavatelja i službene objave burze.</p>
      </section>

      <section>
        <div className="sec-label">4. Korisnički računi</div>
        <p className="imp-p">Registracija se obavlja email adresom i lozinkom.
        Korisnik je odgovoran za tajnost svoje lozinke i za aktivnosti
        provedene kroz svoj račun. Operator može suspendirati ili ukinuti
        račun u slučaju zlouporabe (uključujući pokušaje neovlaštenog
        pristupa, automatizirano masovno preuzimanje ili ometanje rada
        servisa). Funkcionalnost portfelja je evidencijska — temelji se na
        ručnom unosu korisnika, ne povezuje se s brokerskim računima i ne
        izvršava transakcije.</p>
      </section>

      <section>
        <div className="sec-label">5. Intelektualno vlasništvo</div>
        <p className="imp-p">Sadržaj stranice, metodologija, analitički
        tekstovi, vizualizacije i baza podataka vlasništvo su operatora.
        Dopušteno je osobno, nekomercijalno korištenje. Zabranjeni su
        scraping, masovno preuzimanje, sustavno kopiranje i redistribucija
        podataka ili analiza bez prethodnog pisanog dopuštenja operatora.
        Podaci trećih strana (ZSE, izdavatelji) podliježu i pravima tih
        izvora.</p>
      </section>

      <section>
        <div className="sec-label">6. Ograničenje odgovornosti</div>
        <p className="imp-p">U najvećoj mjeri dopuštenoj primjenjivim pravom,
        operator ne odgovara za odluke donesene na temelju sadržaja stranice
        ni za bilo kakvu štetu (izravnu ili neizravnu) nastalu korištenjem ili
        nemogućnošću korištenja stranice, uključujući štetu zbog netočnosti,
        nepotpunosti ili neažurnosti podataka te privremene nedostupnosti
        servisa. Za investicijske, porezne ili pravne odluke potražite
        ovlaštenog savjetnika.</p>
      </section>

      <section>
        <div className="sec-label">7. Izmjene uvjeta</div>
        <p className="imp-p">Operator zadržava pravo izmjene ovih Uvjeta.
        Izmjene se objavljuju na ovoj stranici s datumom stupanja na snagu.
        Nastavak korištenja stranice nakon objave izmjena smatra se
        prihvatom izmijenjenih Uvjeta.</p>
      </section>

      <section>
        <div className="sec-label">8. Mjerodavno pravo i nadležnost</div>
        <p className="imp-p">Na ove Uvjete primjenjuje se pravo Republike
        Hrvatske. Za sporove je nadležan stvarno nadležan sud u Zagrebu.</p>
      </section>

      <section>
        <div className="sec-label">9. Stupanje na snagu</div>
        <p className="imp-p">Ovi Uvjeti stupaju na snagu <b>{UPDATED}</b></p>
      </section>
    </LegalPage>
  )
}

/* =========================== /politika-privatnosti =========================== */

export function PolitikaPrivatnosti() {
  return (
    <LegalPage title="Politika privatnosti">
      <section>
        <div className="sec-label">Voditelj obrade</div>
        <p className="imp-p"><b>Burzovni list</b>, operator stranice
        burzovnilist.com (podaci u <Link to="/impressum">Impressumu</Link>).
        Kontakt za sva pitanja o osobnim podacima:{' '}
        <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a>.</p>
      </section>

      <section>
        <div className="sec-label">Koje podatke obrađujemo i zašto</div>
        <table>
          <thead><tr><th>Podaci</th><th>Svrha</th><th>Pravna osnova</th></tr></thead>
          <tbody>
            <tr>
              <td>email adresa i lozinka (pohranjena isključivo kao hash)</td>
              <td>korisnički račun: registracija, prijava, oporavak lozinke</td>
              <td>izvršenje ugovora (čl. 6. st. 1. t. (b) GDPR)</td>
            </tr>
            <tr>
              <td>podaci o portfelju koje sami unesete (ticker, količina,
                prosječna cijena)</td>
              <td>funkcionalnost „Moj portfelj" — evidencija koju sami vodite</td>
              <td>izvršenje ugovora (čl. 6. st. 1. t. (b) GDPR)</td>
            </tr>
            <tr>
              <td>tehnički/analitički podaci o posjetu (kolačići — Google
                Tag Manager / Google analitika)</td>
              <td>web analitika — razumijevanje korištenja stranice</td>
              <td>privola (čl. 6. st. 1. t. (a) GDPR) — isključivo opt-in;
                bez pristanka se ništa ne učitava</td>
            </tr>
            <tr>
              <td>server logovi (IP adresa, user-agent, vrijeme zahtjeva)</td>
              <td>sigurnost, otkrivanje zlouporabe i otklanjanje kvarova</td>
              <td>legitimni interes (čl. 6. st. 1. t. (f) GDPR)</td>
            </tr>
          </tbody>
        </table>
        <p className="imp-p" style={{ marginTop: 10 }}>Email koristimo
        isključivo za prijavu i oporavak lozinke — bez newslettera i
        marketinga. Napomena: fontovi stranice učitavaju se s Google Fonts
        poslužitelja; pri dohvaćanju fonta vaš preglednik Googleu prenosi IP
        adresu (tehnička nužnost dohvata resursa).</p>
      </section>

      <section>
        <div className="sec-label">Obrađivači i lokacija obrade</div>
        <p className="imp-p"><b>Supabase</b> — autentikacija korisničkih
        računa i baza portfelja; projekt je smješten u regiji{' '}
        <b>eu-central-1 (Frankfurt, EU)</b>. <b>Hostinger</b> — najam
        poslužitelja (VPS) na kojem se stranica poslužuje i na kojem nastaju
        server logovi; obrada unutar EU/EEA. <b>Google</b> (Google Ireland
        Ltd.) — web analitika kroz Google Tag Manager, isključivo uz vašu
        privolu; Google može podatke obrađivati i izvan EU/EEA na temelju
        EU–US okvira za privatnost podataka (Data Privacy Framework) i
        standardnih ugovornih klauzula. Podatke ne prodajemo niti dijelimo s
        trećima u marketinške svrhe.</p>
      </section>

      <section>
        <div className="sec-label">Rokovi čuvanja</div>
        <p className="imp-p">Podaci računa i portfelja čuvaju se dok račun
        postoji, a nakon brisanja računa najviše 30 dana (sigurnosne kopije).
        Server logovi čuvaju se najviše 12 mjeseci. Zapis privole za kolačiće
        vrijedi najviše 12 mjeseci, nakon čega se privola ponovno traži.</p>
      </section>

      <section>
        <div className="sec-label">Vaša prava</div>
        <p className="imp-p">Imate pravo na: pristup svojim podacima,
        ispravak, brisanje („pravo na zaborav"), ograničenje obrade,
        prenosivost podataka, prigovor na obradu temeljenu na legitimnom
        interesu te povlačenje privole u svakom trenutku (bez utjecaja na
        zakonitost obrade prije povlačenja). Privolu za kolačiće povlačite
        kroz „Postavke kolačića" u podnožju stranice.</p>
        <p className="imp-p">Sva prava ostvarujete emailom na{' '}
        <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a> —
        odgovaramo bez nepotrebnog odgađanja, najkasnije u roku 30 dana.
        Imate i pravo pritužbe nadzornom tijelu: Agencija za zaštitu osobnih
        podataka (AZOP), <a href="https://azop.hr" target="_blank"
          rel="noreferrer">azop.hr</a>.</p>
      </section>

      <section>
        <div className="sec-label">Izmjene</div>
        <p className="imp-p">Zadnja izmjena: <b>{UPDATED}</b> Izmjene ove
        politike objavljujemo na ovoj stranici; bitne promjene istaknut ćemo
        pri sljedećem posjetu. Vidi i{' '}
        <Link to="/politika-kolacica">Politiku kolačića</Link> i{' '}
        <Link to="/uvjeti-koristenja">Uvjete korištenja</Link>.</p>
      </section>
    </LegalPage>
  )
}
