import { jsxs, Fragment, jsx } from "react/jsx-runtime";
import { createContext } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server.mjs";
import { Link } from "react-router-dom";
const CONSENT_VERSION = 2;
createContext({
  consent: null,
  openSettings: () => {
  },
  decide: () => {
  }
});
function ImpressumContent() {
  return /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "O servisu" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        /* @__PURE__ */ jsx("b", { children: "Burzovni list" }),
        " — analitička platforma za dionice uvrštene na Zagrebačku burzu. Servis je informativan i edukativan; nije investicijsko društvo, ne pruža investicijsko savjetovanje i ne posreduje u trgovanju."
      ] }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Kontakt: ",
        /* @__PURE__ */ jsx("a", { href: "mailto:info@burzovnilist.com", children: "info@burzovnilist.com" })
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Informativni karakter (MAR)" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Prikazani podaci, rasponi i fer-zone su informativni i analitički — ne predstavljaju investicijski savjet, preporuku ni poticaj na kupnju ili prodaju financijskih instrumenata. Servis ne objavljuje ciljne cijene, rejtinge ni preporuke; položaj tržišne cijene naspram fer-zone je činjenični prikaz uz javno ispisane pretpostavke, a zaključak je uvijek čitateljev. Svaka brojka na stranicama nosi izvor (dokument i stranicu s koje je preuzeta); gdje podatak nije dostupan ili primjenjiv, piše n/p — vrijednosti se ne izmišljaju." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Automatizacija i nadzor" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Analize i procjene na ovom servisu generira automatizirani sustav uz ljudski nadzor. Metode, pravila, parametri i priznate greške sustava javno su opisani na stranici",
        " ",
        /* @__PURE__ */ jsx(Link, { to: "/metodologija", children: "Metodologija" }),
        ", uključujući povijest promjena svake procjene."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Podaci" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Tržišni podaci: službena EOD tečajnica Zagrebačke burze (zse.hr); objavljuje se nakon zatvaranja trgovine, a uz svaku cijenu stoji stvarni datum podatka. Financijski podaci: javno objavljena izvješća izdavatelja (EHO/ZSE). Vrijednosti rijetko trgovanih dionica su indikativne i tako su označene. Unatoč pažnji pri obradi, servis ne jamči potpunu točnost ni pravodobnost podataka — mjerodavni su izvorni dokumenti izdavatelja i službene objave burze." })
    ] }),
    /* @__PURE__ */ jsx("div", { className: "disc", children: "Korištenjem servisa prihvaćate da se sadržaj koristi isključivo u informativne svrhe. Za investicijske, porezne ili pravne odluke potražite ovlaštenog savjetnika." })
  ] });
}
const UPDATED = "15.07.2026.";
const COOKIES = [
  {
    name: "bl_consent",
    purpose: "pamti vaš izbor o kolačićima (verzija politike, datum, odabrane kategorije)",
    cat: "nužni",
    dur: "12 mjeseci",
    party: "prva strana (localStorage)"
  },
  {
    name: "sb-<projekt>-auth-token",
    purpose: "sesija prijavljenog korisnika (Supabase Auth) — postoji samo ako se prijavite",
    cat: "nužni",
    dur: "do odjave / isteka sesije",
    party: "prva strana (localStorage)"
  },
  {
    name: "lastTicker",
    purpose: "pamti zadnju otvorenu dionicu radi navigacijske prečice u zaglavlju",
    cat: "nužni (funkcionalni)",
    dur: "do brisanja iz preglednika",
    party: "prva strana (localStorage)"
  },
  {
    name: "_ga",
    purpose: "Google analitika (učitava se kroz Google Tag Manager) — razlikovanje posjetitelja; postavlja se SAMO ako pristanete na analitičke kolačiće",
    cat: "analitički",
    dur: "do 2 godine",
    party: "treća strana (Google)"
  },
  {
    name: "_ga_*",
    purpose: "Google analitika — stanje sesije po mjernom svojstvu; postavlja se SAMO ako pristanete na analitičke kolačiće",
    cat: "analitički",
    dur: "do 2 godine",
    party: "treća strana (Google)"
  }
];
function PolitikaKolacicaContent({ openSettings }) {
  return /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Što su kolačići i tko ih postavlja" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Kolačići (cookies) i srodne tehnologije lokalne pohrane (localStorage) male su količine podataka koje preglednik čuva na vašem uređaju. Postavlja ih ",
        /* @__PURE__ */ jsx("b", { children: "Burzovni list" }),
        " kao operator ove stranice. Ovaj servis trenutno koristi isključivo pohranu prve strane navedenu u tablici — tehnički kroz localStorage preglednika, na koju se primjenjuju ista pravila privole kao na kolačiće (pohrana na uređaju korisnika)."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Tablica kolačića i lokalne pohrane" }),
      /* @__PURE__ */ jsxs("table", { children: [
        /* @__PURE__ */ jsx("thead", { children: /* @__PURE__ */ jsxs("tr", { children: [
          /* @__PURE__ */ jsx("th", { children: "Naziv" }),
          /* @__PURE__ */ jsx("th", { children: "Svrha" }),
          /* @__PURE__ */ jsx("th", { children: "Kategorija" }),
          /* @__PURE__ */ jsx("th", { children: "Trajanje" }),
          /* @__PURE__ */ jsx("th", { children: "Prva/treća strana" })
        ] }) }),
        /* @__PURE__ */ jsx("tbody", { children: COOKIES.map((c) => /* @__PURE__ */ jsxs("tr", { children: [
          /* @__PURE__ */ jsx("td", { children: /* @__PURE__ */ jsx("code", { children: c.name }) }),
          /* @__PURE__ */ jsx("td", { children: c.purpose }),
          /* @__PURE__ */ jsx("td", { children: c.cat }),
          /* @__PURE__ */ jsx("td", { children: c.dur }),
          /* @__PURE__ */ jsx("td", { className: "fund-src", children: c.party })
        ] }, c.name)) })
      ] }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", style: { marginTop: 10 }, children: [
        /* @__PURE__ */ jsx("b", { children: "Analitika (Google Tag Manager uz Google Consent Mode v2)" }),
        ': prije vašeg pristanka svi su načini pohrane postavljeni na „denied" — analitički kolačići se NE postavljaju. Tek pristankom na kategoriju „Analitički" pohrana prelazi u „granted" i kolačići iz tablice se postavljaju. Povučete li pristanak, pohrana se odmah vraća na „denied", a postojeći ',
        /* @__PURE__ */ jsx("code", { children: "_ga" }),
        "/",
        /* @__PURE__ */ jsx("code", { children: "_ga_*" }),
        " ",
        "kolačići se brišu. Marketinške kolačiće ne koristimo."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Kako upravljati pristankom" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Svoj izbor možete promijeniti ili povući u svakom trenutku — jednako lako kao što je dan:",
        " ",
        /* @__PURE__ */ jsx("button", { type: "button", className: "cc-inline-link", onClick: openSettings, children: "otvori postavke kolačića" }),
        " ",
        "(ista poveznica stoji trajno u podnožju svake stranice). Kolačiće i lokalnu pohranu možete obrisati i u pregledniku: Postavke → Privatnost → Kolačići i podaci stranica (Chrome/Edge), odnosno Postavke → Privatnost i sigurnost (Firefox). Odbijanje ne-nužnih kolačića ne ograničava korištenje stranice."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Pravna osnova" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Nužni kolačići i pohrana: nužnost pružanja usluge koju ste zatražili i legitimni interes operatora (čl. 6. st. 1. t. (b) i (f) GDPR-a; čl. 5. st. 3. ePrivacy direktive — iznimka za strogo nužnu pohranu). Analitički i marketinški kolačići: isključivo vaša privola (čl. 6. st. 1. t. (a) GDPR-a), koju možete povući u svakom trenutku bez posljedica za korištenje stranice." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Verzija i izmjene" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Verzija politike: ",
        /* @__PURE__ */ jsx("b", { children: CONSENT_VERSION }),
        " · zadnja izmjena: ",
        /* @__PURE__ */ jsx("b", { children: UPDATED }),
        " Promijeni li se politika, zapis vašeg pristanka prestaje vrijediti i pri sljedećem posjetu ponovno ćemo vas pitati. Pristanak u svakom slučaju vrijedi najviše 12 mjeseci."
      ] }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Više o obradi osobnih podataka:",
        " ",
        /* @__PURE__ */ jsx(Link, { to: "/politika-privatnosti", children: "Politika privatnosti" }),
        "."
      ] })
    ] })
  ] });
}
function UvjetiKoristenjaContent() {
  return /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "1. Opće odredbe" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Ove Uvjete korištenja primjenjuje ",
        /* @__PURE__ */ jsx("b", { children: "Burzovni list" }),
        ' (dalje: „operator"), pružatelj informativnog servisa na adresi burzovnilist.com — platforme za informativni prikaz podataka i analitičkih raspona za dionice uvrštene na Zagrebačku burzu. Podaci o operatoru i kontakt navedeni su u ',
        /* @__PURE__ */ jsx(Link, { to: "/impressum", children: "Impressumu" }),
        " ",
        "(",
        /* @__PURE__ */ jsx("a", { href: "mailto:info@burzovnilist.com", children: "info@burzovnilist.com" }),
        "). Korištenjem stranice prihvaćate ove Uvjete."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "2. Informativna priroda sadržaja" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Prikazani podaci, rasponi i fer-zone su informativni i analitički — ne predstavljaju investicijski savjet, preporuku ni poziv na kupnju ili prodaju financijskih instrumenata. Fer-zone i rasponi rezultat su javno opisane",
        " ",
        /* @__PURE__ */ jsx(Link, { to: "/metodologija", children: "metodologije" }),
        " s pretpostavkama koje su ispisane uz svaku analizu; zaključak je uvijek čitateljev. Vrijednosti ilikvidnih dionica su indikativne i tako su označene. Servis ne objavljuje ciljne cijene, rejtinge ni preporuke."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "3. Izvori podataka i točnost" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Podaci se temelje na službenim EOD zaključcima Zagrebačke burze (objavljuju se nakon zatvaranja trgovine; mogući je odmak, a uz svaku cijenu stoji stvarni datum podatka) i javno objavljenim izvješćima izdavatelja (EHO/ZSE). Operator ne jamči potpunost, točnost ni ažurnost podataka; podaci koji nedostaju prikazuju se prazni (n/p) i ne procjenjuju se. Mjerodavni su izvorni dokumenti izdavatelja i službene objave burze." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "4. Korisnički računi" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Registracija se obavlja email adresom i lozinkom. Korisnik je odgovoran za tajnost svoje lozinke i za aktivnosti provedene kroz svoj račun. Operator može suspendirati ili ukinuti račun u slučaju zlouporabe (uključujući pokušaje neovlaštenog pristupa, automatizirano masovno preuzimanje ili ometanje rada servisa). Funkcionalnost portfelja je evidencijska — temelji se na ručnom unosu korisnika, ne povezuje se s brokerskim računima i ne izvršava transakcije." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "5. Intelektualno vlasništvo" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Sadržaj stranice, metodologija, analitički tekstovi, vizualizacije i baza podataka vlasništvo su operatora. Dopušteno je osobno, nekomercijalno korištenje. Zabranjeni su scraping, masovno preuzimanje, sustavno kopiranje i redistribucija podataka ili analiza bez prethodnog pisanog dopuštenja operatora. Podaci trećih strana (ZSE, izdavatelji) podliježu i pravima tih izvora." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "6. Ograničenje odgovornosti" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "U najvećoj mjeri dopuštenoj primjenjivim pravom, operator ne odgovara za odluke donesene na temelju sadržaja stranice ni za bilo kakvu štetu (izravnu ili neizravnu) nastalu korištenjem ili nemogućnošću korištenja stranice, uključujući štetu zbog netočnosti, nepotpunosti ili neažurnosti podataka te privremene nedostupnosti servisa. Za investicijske, porezne ili pravne odluke potražite ovlaštenog savjetnika." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "7. Izmjene uvjeta" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Operator zadržava pravo izmjene ovih Uvjeta. Izmjene se objavljuju na ovoj stranici s datumom stupanja na snagu. Nastavak korištenja stranice nakon objave izmjena smatra se prihvatom izmijenjenih Uvjeta." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "8. Mjerodavno pravo i nadležnost" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Na ove Uvjete primjenjuje se pravo Republike Hrvatske. Za sporove je nadležan stvarno nadležan sud u Zagrebu." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "9. Stupanje na snagu" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Ovi Uvjeti stupaju na snagu ",
        /* @__PURE__ */ jsx("b", { children: UPDATED })
      ] })
    ] })
  ] });
}
function PolitikaPrivatnostiContent() {
  return /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Voditelj obrade" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        /* @__PURE__ */ jsx("b", { children: "Burzovni list" }),
        ", operator stranice burzovnilist.com (podaci u ",
        /* @__PURE__ */ jsx(Link, { to: "/impressum", children: "Impressumu" }),
        "). Kontakt za sva pitanja o osobnim podacima:",
        " ",
        /* @__PURE__ */ jsx("a", { href: "mailto:info@burzovnilist.com", children: "info@burzovnilist.com" }),
        "."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Koje podatke obrađujemo i zašto" }),
      /* @__PURE__ */ jsxs("table", { children: [
        /* @__PURE__ */ jsx("thead", { children: /* @__PURE__ */ jsxs("tr", { children: [
          /* @__PURE__ */ jsx("th", { children: "Podaci" }),
          /* @__PURE__ */ jsx("th", { children: "Svrha" }),
          /* @__PURE__ */ jsx("th", { children: "Pravna osnova" })
        ] }) }),
        /* @__PURE__ */ jsxs("tbody", { children: [
          /* @__PURE__ */ jsxs("tr", { children: [
            /* @__PURE__ */ jsx("td", { children: "email adresa i lozinka (pohranjena isključivo kao hash)" }),
            /* @__PURE__ */ jsx("td", { children: "korisnički račun: registracija, prijava, oporavak lozinke" }),
            /* @__PURE__ */ jsx("td", { children: "izvršenje ugovora (čl. 6. st. 1. t. (b) GDPR)" })
          ] }),
          /* @__PURE__ */ jsxs("tr", { children: [
            /* @__PURE__ */ jsx("td", { children: "podaci o portfelju koje sami unesete (ticker, količina, prosječna cijena)" }),
            /* @__PURE__ */ jsx("td", { children: 'funkcionalnost „Moj portfelj" — evidencija koju sami vodite' }),
            /* @__PURE__ */ jsx("td", { children: "izvršenje ugovora (čl. 6. st. 1. t. (b) GDPR)" })
          ] }),
          /* @__PURE__ */ jsxs("tr", { children: [
            /* @__PURE__ */ jsx("td", { children: "tehnički/analitički podaci o posjetu (kolačići — Google Tag Manager / Google analitika)" }),
            /* @__PURE__ */ jsx("td", { children: "web analitika — razumijevanje korištenja stranice" }),
            /* @__PURE__ */ jsx("td", { children: "privola (čl. 6. st. 1. t. (a) GDPR) — isključivo opt-in; bez pristanka se ništa ne učitava" })
          ] }),
          /* @__PURE__ */ jsxs("tr", { children: [
            /* @__PURE__ */ jsx("td", { children: "server logovi (IP adresa, user-agent, vrijeme zahtjeva)" }),
            /* @__PURE__ */ jsx("td", { children: "sigurnost, otkrivanje zlouporabe i otklanjanje kvarova" }),
            /* @__PURE__ */ jsx("td", { children: "legitimni interes (čl. 6. st. 1. t. (f) GDPR)" })
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", style: { marginTop: 10 }, children: "Email koristimo isključivo za prijavu i oporavak lozinke — bez newslettera i marketinga. Napomena: fontovi stranice učitavaju se s Google Fonts poslužitelja; pri dohvaćanju fonta vaš preglednik Googleu prenosi IP adresu (tehnička nužnost dohvata resursa)." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Obrađivači i lokacija obrade" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        /* @__PURE__ */ jsx("b", { children: "Supabase" }),
        " — autentikacija korisničkih računa i baza portfelja; projekt je smješten u regiji",
        " ",
        /* @__PURE__ */ jsx("b", { children: "eu-central-1 (Frankfurt, EU)" }),
        ". ",
        /* @__PURE__ */ jsx("b", { children: "Hostinger" }),
        " — najam poslužitelja (VPS) na kojem se stranica poslužuje i na kojem nastaju server logovi; obrada unutar EU/EEA. ",
        /* @__PURE__ */ jsx("b", { children: "Google" }),
        " (Google Ireland Ltd.) — web analitika kroz Google Tag Manager, isključivo uz vašu privolu; Google može podatke obrađivati i izvan EU/EEA na temelju EU–US okvira za privatnost podataka (Data Privacy Framework) i standardnih ugovornih klauzula. Podatke ne prodajemo niti dijelimo s trećima u marketinške svrhe."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Rokovi čuvanja" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: "Podaci računa i portfelja čuvaju se dok račun postoji, a nakon brisanja računa najviše 30 dana (sigurnosne kopije). Server logovi čuvaju se najviše 12 mjeseci. Zapis privole za kolačiće vrijedi najviše 12 mjeseci, nakon čega se privola ponovno traži." })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Vaša prava" }),
      /* @__PURE__ */ jsx("p", { className: "imp-p", children: 'Imate pravo na: pristup svojim podacima, ispravak, brisanje („pravo na zaborav"), ograničenje obrade, prenosivost podataka, prigovor na obradu temeljenu na legitimnom interesu te povlačenje privole u svakom trenutku (bez utjecaja na zakonitost obrade prije povlačenja). Privolu za kolačiće povlačite kroz „Postavke kolačića" u podnožju stranice.' }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Sva prava ostvarujete emailom na",
        " ",
        /* @__PURE__ */ jsx("a", { href: "mailto:info@burzovnilist.com", children: "info@burzovnilist.com" }),
        " — odgovaramo bez nepotrebnog odgađanja, najkasnije u roku 30 dana. Imate i pravo pritužbe nadzornom tijelu: Agencija za zaštitu osobnih podataka (AZOP), ",
        /* @__PURE__ */ jsx(
          "a",
          {
            href: "https://azop.hr",
            target: "_blank",
            rel: "noreferrer",
            children: "azop.hr"
          }
        ),
        "."
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { children: [
      /* @__PURE__ */ jsx("div", { className: "sec-label", children: "Izmjene" }),
      /* @__PURE__ */ jsxs("p", { className: "imp-p", children: [
        "Zadnja izmjena: ",
        /* @__PURE__ */ jsx("b", { children: UPDATED }),
        " Izmjene ove politike objavljujemo na ovoj stranici; bitne promjene istaknut ćemo pri sljedećem posjetu. Vidi i",
        " ",
        /* @__PURE__ */ jsx(Link, { to: "/politika-kolacica", children: "Politiku kolačića" }),
        " i",
        " ",
        /* @__PURE__ */ jsx(Link, { to: "/uvjeti-koristenja", children: "Uvjete korištenja" }),
        "."
      ] })
    ] })
  ] });
}
const CONTENT = {
  "/impressum": ImpressumContent,
  "/uvjeti-koristenja": UvjetiKoristenjaContent,
  "/politika-privatnosti": PolitikaPrivatnostiContent,
  "/politika-kolacica": PolitikaKolacicaContent
};
function renderStatic(route) {
  const C = CONTENT[route];
  if (!C) return null;
  return renderToStaticMarkup(
    /* @__PURE__ */ jsx(StaticRouter, { location: route, children: /* @__PURE__ */ jsx(C, {}) })
  );
}
export {
  renderStatic
};
