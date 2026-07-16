# Changelog (tehnički — interni)

## 16.07.2026. — M33: SSG regresija i rupe u indeksabilnosti

### Nalaz: /screener, /dividende, /usporedba prazne za crawlere — UZROK

Forenzika git povijesti `frontend/scripts/prerender.mjs`:

- Te rute **nikad nisu imale statički body** — od uvođenja prerendera (M25)
  pa kroz Z5, M27, M29 i M32, njihovi unosi u prerenderu sadržavali su SAMO
  `title` + `description` (provjereno na commitovima 7010a22, d9a0565,
  609d45a). Body su imali jedino `/` i `/metodologija`.
- Dakle **nije naknadna regresija koda** (M29/M32 refaktori su vjerno
  prenijeli postojeće stanje), nego **lažno pozitivan acceptance u Z5**:
  provjera "curl /usporedba vraća sadržaj bez JS-a" prošla je na meta
  tagovima/naslovu i Playwright provjeri s uključenim JS-om — nikad nije
  postojala provjera da statički HTML sadrži PODATKE.
- Zašto testovi to nisu uhvatili: `tests/test_sitemap.py` (M29) provjeravao
  je samo da stranica POSTOJI i da je u sitemapu — ne i da ima sadržaj.

Sanacija (M33): statične tablice s punim imenima i podacima za sve tri rute
+ naslovnica s imenima firmi + jedinstveni statički footer s pravnim
linkovima na SVIM rutama + pravne stranice SSR-ane iz istih React komponenti
+ **content-marker test** (`test_content_markeri_*`) koji pada ako bilo koja
indeksabilna ruta postane prazna ljuska (min. tekst, H1, footer linkovi,
min. broj redaka za tablične rute). Negativno dokazano: ispražnjena
/usporedba ruši test sa 6 grešaka.

### Nalaz: PODR fer-zona 14–53 € — ARTEFAKT (popravljeno, metodologija v2.3)

Sidro (DCF-FCF) degenerirano: raspon osjetljivosti širi od 100% vlastite
baze (14–53 uz bazu ~33), u zadnjem DB runu baza čak negativna (−8,4 €/dion.)
— posljedica izvanrednih ulaza u godini akvizicije, dok potvrdne metode
(EV/EBITDA, opravdani P/B, relativni multipli) stoje 147–269 €. Dodano
crveno pravilo (v2.3, `src/valuation_methods.py::reconcile`): sidro s
rasponom > 100% baze pada na sljedeći pristup u hijerarhiji, uz vidljivu
napomenu. Učinak na univerzum: promijenjena SAMO PODR zona (14–53 → 246–333,
sidro comps). ADRS=PODR=160,00 € potvrđeno kao slučajnost — nije dirano.
