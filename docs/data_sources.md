# Izvori podataka — potpuni registar (M23, DIO B)

Za svaki tip podatka: odakle dolazi, kako se čita, gdje je krhak i kada je
zadnji put provjereno. Pravilo platforme: **ništa izmišljeno, n/p nije 0** —
kad izvor pukne, polje ostaje prazno s razlogom, ne procjenjuje se.

Zadnja cjelovita provjera svih izvora: **14.07.2026.**

---

## 1. Cijene (EOD)

- **Izvor**: službena tečajnica ZSE —
  `https://rest.zse.hr/web/<token>/price-list/XZAG/{datum}/json` (dnevni EOD
  za sve papire); povijesni backfill po papiru:
  `https://zse.hr/json/securityHistory/{isin}/{od}/{do}/hr`. Indeksi:
  `https://zse.hr/json/indexHistory/...` i `IndexComposition`.
- **Način čitanja**: scrape javnog JSON-a, bez API ključa; noćni prolaz
  (`src/daily.py`) upisuje u `prices_eod` s izvorom po retku. Cijene su
  službeni zaključci s **danom zaostatka** (piše na svakoj stranici weba).
- **Krhkost**: token u REST putanji nije dokumentiran i ZSE ga može
  rotirati; format JSON-a nije verzioniran. Fallback: mojedionice.com
  (koristi se samo ako ZSE ne odgovara, izvor se bilježi). Nelikvidni papiri
  danima nemaju trgovanja — zadnja cijena može biti stara (prikazuje se
  datum, likvidnost se označava uz cijenu).
- **Zadnja provjera**: 14.07.2026. (noćni prolaz radi).

## 2. Financijska izvješća

- **Izvor**: EHO registar propisanih informacija — feed
  `https://eho.zse.hr/feed` (objave izdavatelja s privicima PDF/XLSX);
  dokumenti se spremaju u `data/reports/` i `data/reports/auto/`.
- **Način čitanja**: deterministički parseri po obrascu — TFI-POD XLSX
  (`scripts/parse_tfi_universe.py`, uklj. varijantu financijskih usluga sa
  sekcijama A–J i NT-D izravnu metodu novčanog toka), nadzorni godišnji
  obrazac banaka (`scripts/parse_bank_universe.py`), FINREP kvartalni
  obrazac banaka i ISD/IFP obrazac osiguranja
  (`scripts/backfill_fin_interim.py`). Svaki parser ima sanity gate
  (AOP + naziv retka moraju se poklopiti); PDF-only izvješća idu kroz
  LLM ekstrakciju (`src/extract.py`) pa kroz `validate` gate — što ne
  prođe, ostaje `needs_review` i NE ulazi u analizu.
- **Krhkost**: izdavatelji mijenjaju obrasce (ZB varijanta, IFRS 17 kod
  osiguranja); mali izdavatelji objavljuju samo PDF (skener) — OCR kvaliteta
  varira; EHO feed povremeno kasni za objavom na stranici izdavatelja.
  Svaka brojka u bazi nosi dokument + stranicu.
- **Zadnja provjera**: 14.07.2026. (M20 sweep — 0 anomalija zona).

## 3. Dividende

- **Izvor**: ZSE stranica papira `https://zse.hr/hr/papir/310?isin=...`
  (blok korporativnih akcija: iznos, ex-datum, record, isplata) + EHO objave
  (prijedlozi uprava prije glavne skupštine).
- **Način čitanja**: scrape stranice papira po klasi dionice
  (`scripts/scrape_dividends_zse.py`); status (isplaćeno / nadolazeće /
  prijedlog) izvodi se iz datuma i teksta objave, nikad se ne pogađa.
  Agregirani kalendar: `scripts/build_dividende.py` (noćno).
- **Krhkost**: stranica papira je HTML bez verzioniranog API-ja — promjena
  predloška lomi scrape (gate: nevaljan red se preskače s razlogom).
  Prijedlog dividende NIJE isplata — vizualno razlikovano na /dividende.
- **Zadnja provjera**: 14.07.2026.

## 4. Broj dionica / ISIN / klase

- **Izvor**: ZSE stranica papira — polje „Uvrštena količina", ISIN, oznaka
  klase; NACE djelatnost s iste stranice.
- **Način čitanja**: scrape (`scripts/seed_shares_zse.py`) u
  `share_classes`; trezorske dionice iz godišnjih izvješća (bilješke).
- **Krhkost**: uvrštena količina ≠ izdana količina kod rijetkih izdavatelja
  (dokap u tijeku); promjene nakon dokapitalizacija kasne dan-dva. EPS/BVPS
  se računaju na broju dionica s izvorom — nesklad ruši validaciju.
- **Zadnja provjera**: 14.07.2026.

## 5. Dioničari (top 10)

- **Izvor 1 (tekući)**: ZSE stranica papira ugrađuje `top_shareholders`
  JSON u HTML (izvor SKDD) — `scripts/scrape_shareholders_zse.py`, svih
  69 firmi. Stranica NE objavljuje as-of datum liste → snapshot_date je
  datum dohvata (dokumentirano u `source_detail` svakog retka).
- **Izvor 2 (povijesni)**: tablica „10 najvećih dioničara / vlasnička
  struktura" iz lokalnih godišnjih izvješća
  (`scripts/extract_shareholders_reports.py`) — strogi deterministički
  parser (≥5 redova, rangovi uzastopni od 1, Σ ≤ 100,5%), svaki red citira
  PDF + stranicu; snapshot = 31.12. fiskalne godine.
- **Način čitanja**: upis u tablicu `shareholders`; skrbnički/zbirni računi
  označeni `is_custody` (nisu stvarni krajnji vlasnici). PROMJENE = diff
  zadnja dva snapshota po firmi (normalizacija imena samo za sparivanje —
  prikaz uvijek točno kako je objavljeno); jedan snapshot → stanje s
  datumom, bez izmišljenih promjena. Mjesečni snapshot: 1. u mjesecu iz
  noćnog prolaza.
- **Krhkost**: `top_shareholders` blok je nedokumentiran (može nestati);
  ZSE imenuje pozicije preko skrbnika („BANKA/KLIJENT"), izvješća imenuju
  krajnjeg imatelja — diff preko izvora zato koristi klijentski dio zapisa;
  PDF tablice dioničara često su fragmentirane (22 od 25 izvješća pošteno
  preskočeno umjesto krive tablice).
- **Zadnja provjera**: 14.07.2026. (scrape ok=69).

## 6. Nerizična stopa (rf) i premija rizika (ERP)

- **Izvor**: rf = 3,61% — prinos HR 10-godišnje državne obveznice
  (TradingEconomics, sredina lipnja 2026; ZSE obveznice preslabo likvidne
  za primarni izvor). ERP = 5,7% — Damodaranova tablica (pages.stern.nyu.edu,
  siječanj 2026, zreli ERP + country risk premium za HR); točna decimala
  označena `erp_exact_unverified`.
- **Način čitanja**: ručna kalibracija s citatom u
  `src/params_calibrated.py` (RF_SRC/ERP_SRC) — NIJE automatski scrape;
  svaka valuacija nosi puni citat parametara.
- **Krhkost**: statična vrijednost — zastarijeva; revizija uz svaku
  rekalibraciju (docs/calibration.md). Promjena rf za ±0,5 p.p. pomiče
  DCF/DDM zone — zato je osjetljivost dio svake zone.
- **Zadnja provjera**: 14.07.2026. (vrijednosti iz lipnja 2026.).

## 7. Peer multipli

- **Izvor**: vlastita baza — peer skupovi po firmi s kriterijima u
  `docs/peers.md` (likvidnost ispred savršene sektorske podudarnosti; bez
  cirkularnosti — ovisna društva nisu peeri); medijan P/E, P/B, EV/EBITDA
  računa `src/peer_multiples.py` iz cijena + zadnjih godišnjih
  konsolidiranih financija.
- **Način čitanja**: izračun iz `financials` + `prices_eod` (kalibracija u
  `src/params_calibrated.py`); strani/regionalni peeri se NE scrapeaju —
  premala usporedivost, koristi se domaći presjek.
- **Krhkost**: plitko tržište → medijan zna biti na 3–5 firmi; sektor bez
  usporedivog peera (npr. osiguranje) ne dobiva peer-metodu — metoda se
  preskače s razlogom, ne nateže.
- **Zadnja provjera**: 14.07.2026.

## 8. Vijesti / objave

- **Izvor**: EHO feed (`https://eho.zse.hr/feed`) — službene objave
  izdavatelja.
- **Način čitanja**: noćni uvoz (`scripts/import_news.py`), klasifikacija
  naslova; MAR-osjetljive objave samo se prenose, ne interpretiraju.
- **Krhkost**: feed nema garantiran SLA; naslovi izdavatelja neujednačeni.
- **Zadnja provjera**: 14.07.2026.

---

## Zajednička pravila

1. **Svaka brojka nosi izvor** (URL / dokument + stranica) — vidljivo i u
   bazi i na webu.
2. **Gate umjesto pogađanja**: parser koji nije siguran vraća „preskočeno s
   razlogom", nikad približnu tablicu.
3. **n/p ≠ 0**: prazno polje je informacija („nema u bazi"), nula je
   tvrdnja.
4. **Datumi zaostatka su deklarirani**: cijene EOD s danom zaostatka;
   SKDD lista bez objavljenog as-of datuma nosi datum dohvata.
5. **Krhki izvori imaju fallback ili alarm**: pad scrapea ide u dnevni
   digest, ne u tihu rupu.
