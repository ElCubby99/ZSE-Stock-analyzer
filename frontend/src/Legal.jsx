import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { CONSENT_VERSION, useConsent } from './consent.jsx'
import { useLang } from './i18n/LangContext.jsx'

/* M24: tri pravne stranice — Politika kolačića, Uvjeti korištenja,
   Politika privatnosti. Isti layout kao Impressum. Dostupne bez prijave i
   bez pristanka na kolačiće. Tablica kolačića odražava STVARNO stanje
   (bl_consent, sb-* auth, lastTicker; analitika još nije uvedena). */

const UPDATED = '17.07.2026.'

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

/* Content komponente su ČISTE (bez hookova) — iste ih koristi SPA (kroz
   wrapper s LegalPage) i prerender (SSR u statički HTML, jedan izvor teksta). */
export function PolitikaKolacicaContent({ openSettings }) {
  return (
    <>
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
        <div className="mk-scroll">
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
        </div>
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
    </>
  )
}

export function PolitikaKolacica() {
  const { openSettings } = useConsent()
  const { lang } = useLang()
  if (lang === 'en') {
    return (
      <LegalPage title="Cookie Policy">
        <EnCookiesContent openSettings={openSettings} />
      </LegalPage>
    )
  }
  return (
    <LegalPage title="Politika kolačića">
      <PolitikaKolacicaContent openSettings={openSettings} />
    </LegalPage>
  )
}

/* ============================ /uvjeti-koristenja ============================ */

export function UvjetiKoristenjaContent() {
  return (
    <>
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
    </>
  )
}

export function UvjetiKoristenja() {
  const { lang } = useLang()
  if (lang === 'en') {
    return <LegalPage title="Terms of Use"><EnTermsContent /></LegalPage>
  }
  return (
    <LegalPage title="Uvjeti korištenja">
      <UvjetiKoristenjaContent />
    </LegalPage>
  )
}

/* =========================== /politika-privatnosti =========================== */

export function PolitikaPrivatnostiContent() {
  return (
    <>
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
        <b>eu-central-1 (Frankfurt, EU)</b>. <b>Vercel Inc.</b> (SAD) —
        hosting i posluživanje stranice preko globalne CDN mreže; kod
        Vercela nastaju server logovi. Prijenos podataka u SAD temelji se
        na EU–US okviru za privatnost podataka (Data Privacy Framework) i
        standardnim ugovornim klauzulama. <b>Google</b> (Google Ireland
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
    </>
  )
}

export function PolitikaPrivatnosti() {
  const { lang } = useLang()
  if (lang === 'en') {
    return <LegalPage title="Privacy Policy"><EnPrivacyContent /></LegalPage>
  }
  return (
    <LegalPage title="Politika privatnosti">
      <PolitikaPrivatnostiContent />
    </LegalPage>
  )
}

/* ==================== M38: ENGLESKE VERZIJE (pun prijevod) ====================
   Content komponente su čiste (bez hookova) — koristi ih SPA i prerender.
   Svaka nosi "prevails" klauzulu: u slučaju spora mjerodavna je hrvatska
   verzija. Prijevodi prate docs/glossary_hr_en.md. */

const PrevailsNote = ({ hrPath }) => (
  <section>
    <div className="sec-label">Language</div>
    <p className="imp-p">This is an English translation provided for
    convenience. <b>In case of dispute, the Croatian version prevails</b>:{' '}
    <Link to={hrPath}>Croatian version</Link>.</p>
  </section>
)

const COOKIES_EN = [
  { name: 'bl_consent',
    purpose: 'remembers your cookie choice (policy version, date, selected categories)',
    cat: 'strictly necessary', dur: '12 months', party: 'first party (localStorage)' },
  { name: 'sb-<project>-auth-token',
    purpose: 'logged-in user session (Supabase Auth) — exists only if you sign in',
    cat: 'strictly necessary', dur: 'until sign-out / session expiry', party: 'first party (localStorage)' },
  { name: 'lastTicker',
    purpose: 'remembers the last opened stock for the header navigation shortcut',
    cat: 'necessary (functional)', dur: 'until deleted from the browser', party: 'first party (localStorage)' },
  { name: '_ga',
    purpose: 'Google analytics (loaded via Google Tag Manager) — distinguishes visitors; set ONLY if you consent to analytics cookies',
    cat: 'analytics', dur: 'up to 2 years', party: 'third party (Google)' },
  { name: '_ga_*',
    purpose: 'Google analytics — session state per measurement property; set ONLY if you consent to analytics cookies',
    cat: 'analytics', dur: 'up to 2 years', party: 'third party (Google)' },
]

export function EnCookiesContent({ openSettings }) {
  return (
    <>
      <section>
        <div className="sec-label">What cookies are and who sets them</div>
        <p className="imp-p">Cookies and related local-storage technologies
        (localStorage) are small amounts of data your browser keeps on your
        device. They are set by <b>Burzovni list</b> as the operator of this
        site. The service currently uses exclusively the first-party storage
        listed in the table — technically via the browser's localStorage, to
        which the same consent rules apply as to cookies (storage on the
        user's device).</p>
      </section>

      <section>
        <div className="sec-label">Table of cookies and local storage</div>
        <div className="mk-scroll">
        <table>
          <thead><tr><th>Name</th><th>Purpose</th><th>Category</th>
            <th>Duration</th><th>First/third party</th></tr></thead>
          <tbody>
            {COOKIES_EN.map((c) => (
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
        </div>
        <p className="imp-p" style={{ marginTop: 10 }}>
          <b>Analytics (Google Tag Manager with Google Consent Mode v2)</b>:
          before your consent, all storage modes are set to "denied" —
          analytics cookies are NOT set. Only when you consent to the
          "Analytics" category does storage switch to "granted" and the
          cookies in the table get set. If you withdraw consent, storage
          immediately returns to "denied" and existing{' '}
          <code>_ga</code>/<code>_ga_*</code> cookies are deleted. We use no
          marketing cookies.
        </p>
      </section>

      <section>
        <div className="sec-label">Managing your consent</div>
        <p className="imp-p">You can change or withdraw your choice at any
        time — as easily as it was given:{' '}
        <button type="button" className="cc-inline-link" onClick={openSettings}>
          open cookie settings
        </button>{' '}
        (the same link is permanently in the footer of every page). You can
        also delete cookies and local storage in your browser: Settings →
        Privacy → Cookies and site data (Chrome/Edge) or Settings → Privacy
        &amp; Security (Firefox). Declining non-essential cookies does not
        limit your use of the site.</p>
      </section>

      <section>
        <div className="sec-label">Legal basis</div>
        <p className="imp-p">Strictly necessary cookies and storage: necessity
        of providing the service you requested and the operator's legitimate
        interest (Art. 6(1)(b) and (f) GDPR; Art. 5(3) of the ePrivacy
        Directive — the strictly-necessary exemption). Analytics and
        marketing cookies: exclusively your consent (Art. 6(1)(a) GDPR),
        which you can withdraw at any time without consequences for using
        the site.</p>
      </section>

      <section>
        <div className="sec-label">Version and changes</div>
        <p className="imp-p">Policy version: <b>{CONSENT_VERSION}</b> · last
        change: <b>{UPDATED}</b> If the policy changes, your recorded consent
        expires and we will ask again on your next visit. Consent is in any
        case valid for at most 12 months.</p>
        <p className="imp-p">More about personal-data processing:{' '}
        <Link to="/en/privacy">Privacy Policy</Link>.</p>
      </section>
      <PrevailsNote hrPath="/politika-kolacica" />
    </>
  )
}

export function EnTermsContent() {
  return (
    <>
      <section>
        <div className="sec-label">1. General provisions</div>
        <p className="imp-p">These Terms of Use are applied by <b>Burzovni
        list</b> (the "operator"), the provider of the informational service
        at burzovnilist.com — a platform for the informational display of
        data and analytical ranges for stocks listed on the Zagreb Stock
        Exchange. Operator details and contact are in the{' '}
        <a href="/impressum">Impressum</a>{' '}
        (<a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a>).
        By using the site you accept these Terms.</p>
      </section>

      <section>
        <div className="sec-label">2. Informational nature of the content</div>
        <p className="imp-p">The data, ranges and fair-value zones shown are
        informational and analytical — they are not investment advice, a
        recommendation, or a solicitation to buy or sell financial
        instruments. Fair-value zones and ranges result from a publicly
        described <Link to="/en/methodology">methodology</Link> with
        assumptions stated next to every analysis; the conclusion is always
        the reader's. Values of illiquid stocks are indicative and tagged as
        such. The service publishes no target prices, ratings or
        recommendations.</p>
      </section>

      <section>
        <div className="sec-label">3. Data sources and accuracy</div>
        <p className="imp-p">The data is based on official end-of-day closes
        of the Zagreb Stock Exchange (published after the close of trading; a
        delay is possible, and every price carries the actual data date) and
        issuers' publicly available reports (EHO/ZSE). The operator does not
        guarantee completeness, accuracy or timeliness; missing data is shown
        empty (n/a) and is never estimated. The issuers' source documents and
        the exchange's official publications are authoritative.</p>
      </section>

      <section>
        <div className="sec-label">4. User accounts</div>
        <p className="imp-p">Registration uses an email address and password.
        The user is responsible for the confidentiality of their password and
        for activity under their account. The operator may suspend or
        terminate an account in case of abuse (including unauthorized-access
        attempts, automated bulk downloading, or disrupting the service).
        The portfolio feature is a record-keeping tool — it is based on the
        user's manual entries, does not connect to brokerage accounts and
        executes no transactions.</p>
      </section>

      <section>
        <div className="sec-label">5. Intellectual property</div>
        <p className="imp-p">The site's content, methodology, analytical
        texts, visualizations and database are the operator's property.
        Personal, non-commercial use is permitted. Scraping, bulk
        downloading, systematic copying and redistribution of data or
        analyses without the operator's prior written permission are
        prohibited. Third-party data (ZSE, issuers) is additionally subject
        to those sources' rights.</p>
      </section>

      <section>
        <div className="sec-label">6. Limitation of liability</div>
        <p className="imp-p">To the fullest extent permitted by applicable
        law, the operator is not liable for decisions made on the basis of
        the site's content, nor for any damage (direct or indirect) arising
        from the use of, or inability to use, the site — including damage
        due to inaccuracy, incompleteness or untimeliness of data and
        temporary unavailability of the service. For investment, tax or
        legal decisions, consult a licensed adviser.</p>
      </section>

      <section>
        <div className="sec-label">7. Changes to the Terms</div>
        <p className="imp-p">The operator reserves the right to amend these
        Terms. Amendments are published on this page with their effective
        date. Continued use of the site after publication constitutes
        acceptance of the amended Terms.</p>
      </section>

      <section>
        <div className="sec-label">8. Governing law and jurisdiction</div>
        <p className="imp-p">These Terms are governed by the law of the
        Republic of Croatia. The court with subject-matter jurisdiction in
        Zagreb has jurisdiction over disputes.</p>
      </section>

      <section>
        <div className="sec-label">9. Effective date</div>
        <p className="imp-p">These Terms take effect on <b>{UPDATED}</b></p>
      </section>
      <PrevailsNote hrPath="/uvjeti-koristenja" />
    </>
  )
}

export function EnPrivacyContent() {
  return (
    <>
      <section>
        <div className="sec-label">Controller</div>
        <p className="imp-p"><b>Burzovni list</b>, operator of
        burzovnilist.com (details in the <a href="/impressum">Impressum</a>).
        Contact for all personal-data questions:{' '}
        <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a>.</p>
      </section>

      <section>
        <div className="sec-label">What data we process and why</div>
        <div className="mk-scroll">
        <table>
          <thead><tr><th>Data</th><th>Purpose</th><th>Legal basis</th></tr></thead>
          <tbody>
            <tr>
              <td>email address and password (stored exclusively as a hash)</td>
              <td>user account: registration, sign-in, password recovery</td>
              <td>performance of a contract (Art. 6(1)(b) GDPR)</td>
            </tr>
            <tr>
              <td>portfolio data you enter yourself (ticker, quantity,
                average price)</td>
              <td>the "My portfolio" feature — a record you keep yourself</td>
              <td>performance of a contract (Art. 6(1)(b) GDPR)</td>
            </tr>
            <tr>
              <td>technical/analytics visit data (cookies — Google Tag
                Manager / Google analytics)</td>
              <td>web analytics — understanding how the site is used</td>
              <td>consent (Art. 6(1)(a) GDPR) — strictly opt-in; nothing
                loads without consent</td>
            </tr>
            <tr>
              <td>server logs (IP address, user agent, request time)</td>
              <td>security, abuse detection and troubleshooting</td>
              <td>legitimate interest (Art. 6(1)(f) GDPR)</td>
            </tr>
          </tbody>
        </table>
        </div>
        <p className="imp-p" style={{ marginTop: 10 }}>We use email
        exclusively for sign-in and password recovery — no newsletters, no
        marketing. Note: the site's fonts load from Google Fonts servers;
        when fetching a font your browser transmits your IP address to
        Google (a technical necessity of resource loading).</p>
      </section>

      <section>
        <div className="sec-label">Processors and processing location</div>
        <p className="imp-p"><b>Supabase</b> — user-account authentication
        and the portfolio database; the project is hosted in the{' '}
        <b>eu-central-1 region (Frankfurt, EU)</b>. <b>Vercel Inc.</b>
        (USA) — hosting and serving of the site via a global CDN; server
        logs arise at Vercel. Transfers to the USA rely on the EU–US Data
        Privacy Framework and standard contractual clauses. <b>Google</b>
        (Google Ireland Ltd.) — web analytics via Google Tag Manager,
        strictly with your consent; Google may process data outside the
        EU/EEA on the basis of the EU–US Data Privacy Framework and standard
        contractual clauses. We do not sell data, nor share it with third
        parties for marketing purposes.</p>
      </section>

      <section>
        <div className="sec-label">Retention periods</div>
        <p className="imp-p">Account and portfolio data is kept while the
        account exists, and for at most 30 days after account deletion
        (backups). Server logs are kept for at most 12 months. The cookie
        consent record is valid for at most 12 months, after which consent
        is requested again.</p>
      </section>

      <section>
        <div className="sec-label">Your rights</div>
        <p className="imp-p">You have the right to: access your data,
        rectification, erasure ("right to be forgotten"), restriction of
        processing, data portability, objection to processing based on
        legitimate interest, and withdrawal of consent at any time (without
        affecting the lawfulness of processing before withdrawal). Cookie
        consent is withdrawn via "Cookie settings" in the footer of every
        page.</p>
        <p className="imp-p">You exercise all rights by email to{' '}
        <a href="mailto:info@burzovnilist.com">info@burzovnilist.com</a> —
        we respond without undue delay, at the latest within 30 days. You
        also have the right to complain to the supervisory authority: the
        Croatian Personal Data Protection Agency (AZOP),{' '}
        <a href="https://azop.hr" target="_blank" rel="noreferrer">azop.hr</a>.</p>
      </section>

      <section>
        <div className="sec-label">Changes</div>
        <p className="imp-p">Last change: <b>{UPDATED}</b> Changes to this
        policy are published on this page; material changes will be
        highlighted on your next visit. See also the{' '}
        <Link to="/en/cookies">Cookie Policy</Link> and{' '}
        <Link to="/en/terms">Terms of Use</Link>.</p>
      </section>
      <PrevailsNote hrPath="/politika-privatnosti" />
    </>
  )
}
