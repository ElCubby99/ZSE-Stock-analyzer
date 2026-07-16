# Changelog (tehnički — interni)

## 2026-07-16 — M34: satni EOD pokušaji + forenzika incidenta

### Forenzika 16.07. (cijene nisu osvježene do ~19:00)

Tri neovisna uzroka, svaki dokumentiran iz Actions logova i baze:

1. **GitHub cron kasni + preuzak DST guard**: cron `20 14` (16:20 CEST)
   ispalio je tek u 17:49 lokalno (kašnjenje ~1,5 h), cron `20 15` u
   18:44; DST guard je propuštao samo lokalni sat "16", pa su OBA
   zakazana runa završila kao no-op "izvan prozora — preskačem"
   (runovi 29512853277 i 29516824533, oba SUCCESS bez posla).
   **Nijedan zakazani run danas nije ni pokušao dohvat.**
2. **Podaci SU bili dostupni najkasnije u 19:08**: Borisov ručni
   dispatch (19:07:54) povukao je 65/69 EOD zapisa u PRVOM pokušaju
   (run 29518493362). Točno vrijeme ZSE objave nepoznato je jer nijedan
   raniji run nije provjeravao — kalibracija: satni termini 16:20–22:20
   pokrivaju i ovakva kašnjenja.
3. **Dispatch run je svejedno pao (exit 1) u regen fazi** — produkcijska
   Supabase baza NEMA v3 shemu (stupci `dividends.payout_type` i dr.
   dodavani su runtime DDL-om samo u lokalnoj bazi):
   `scripts.build_dividende` pao je na nepostojećem stupcu;
   u `build_ctx` je SQL greška ostavila transakciju aborted, per-ticker
   handler NIJE radio rollback pa je `log()` digao
   `InFailedSqlTransaction` i srušio cijeli run prije regena/commita
   (zato je `pipeline_runs` za daily-2026-07-16 prazan — rollback outer
   transakcije). Cijene su preživjele (zaseban connection u
   `fetch_zse_json`), ali exporti/deploy nisu — sajt ostao na 15.07.
   Bonus nalaz: watcher pao na `credit balance too low` (Anthropic API).

### Novi dizajn (M34)

- Workflow: satni cronovi `20 14-20` (CEST) + `20 15-21` (CET) radnim
  danima; DST guard proširen na lokalno 16–23 h; `workflow_dispatch`
  ostaje; concurrency nepromijenjen; timeout 130 → 30 min.
- `src/daily.py`: (1) `ensure_schema` — idempotentna migracija
  `db/zse_schema_v3_1.sql` na početku svakog runa (konsolidiran SAV
  runtime DDL; produkcija se sama zakrpa); (2) `eod_already_done`
  guard (udio klasa ≥ 0,5); (3) `stage_prices` = JEDAN pokušaj bez
  sleep petlje (interna retry-do-18:00 petlja UKLONJENA — čekanje rade
  cronovi); (4) "not yet" = exit 0 + log "pokušaj N od M" (SUCCESS,
  bez lažnih alarma); (5) exit 3 SAMO kad zadnji pokušaj (≥22 h) nema
  podatke → issue + mail, jednom dnevno; (6) backfill prethodnog
  trgovinskog dana u istom uspješnom runu; (7) watcher/extract/regen
  se rade samo u runu koji je našao podatke; (8) rollback higijena:
  per-ticker regen rollback + `log()` otporan na aborted transakciju.
- Workflow koraci nakon daily.py gate-ani na `did_work` (no-op run ne
  troši API pozive za vijesti niti dira commit/deploy).
- Testovi: `tests/test_eod_hourly.py` (10 simulacija po acceptance
  kriterijima; stari `test_daily_readiness.py` uklonjen s dizajnom).
- Procjena minuta: ~5–8 min/dan (~110–175 min/mj) — u README-u,
  stvarna potrošnja se upisuje nakon prvog tjedna.

## 2026-07-16 — Metodologija v3.1: dividendni pod + kompozitni g1

### DIO 1 — dividendni pod (sanity test iz veta u ULAZ)

Priznata greška: suspenzija zone ("u rekalibraciji") bila je dizajnerska
greška — najtvrđi dokaz (održiva dividenda) treba ulaziti u procjenu, ne
gasiti je. Novo (`src/valuation_methods.py::reconcile`): kad zona pada na
testu, V_div = D_sust/(r − g_prag) — ISTI pragovi kao test (2,5% kapitalna
sidra, 4% DCF/DDM), bez novih parametara — ulazi među kvalificirane metode
(conf 0,8), medijan se preračuna, donji rub se podigne barem do V_div
(floor clamp, min širina ×1,05) i test se PONOVI nad novom zonom; verdikt
"prolazi (uz dividendni pod)". Suspenzija kao ishod ne postoji;
`recalibrating` je uvijek None (ključ zadržan radi kompatibilnosti);
"u rekalibraciji" uklonjeno iz SVIH UI grana (Shell/MarketProfile/
StockPage/Screener/Legend/Metodologija/build_overview/distribucijski_alarm).
Učinak: 5 nekad suspendiranih imena s objavljenim zonama — ATGR
40,40–43,00; HT 50,68–70,39; QTLG 1,12–2,14 (pod više nije potreban —
prolazi prirodno s kompozitnim g1); RIVP 4,40–4,86; ZB 1,36–1,42.
Kontrole: ZABA 23,22–32,95 i CROS 1.823,40–2.496,43 NEPROMIJENJENE.

### DIO 2 — kompozitna stopa rasta g1

Priznata greška: kratka serija izvodila je g1 iz JEDNE godišnje usporedbe
(TTM vs lani) — jedna godina mjeri jednokratne i bazne efekte, ne stopu
rasta. Novo (`src/valuation_methods.py::composite_g1`): g1 = medijan
{g_obs (3g CAGR, samo ≥3 godišnja izvješća), g_sust = ROE_TTM × (1 −
payout_sust; bez dividende g_sust = ROE), g_terminal}; cap NAKON medijana
(10% sa serijom / 8% bez); g1 < 0 samo uz negativan g_obs iz ≥3g serije;
TVRDI clamp g1 ≤ r − 0,5 p.b. (uklj. zaštitu od round-up preko clampa —
otkriveno na PODR). TTM-vs-lani ostaje SAMO kontekst. Reverse-DCF sada
uspoređuje protiv "naš kompozitni rast (serija/održivi/terminal)", prag
plauzibilnosti |implied − g1| ≤ 2 p.b. (staro 3 p.b.), proturječje "nema
serije u bazi" uklonjeno. UI: kartica "Rast eksplicitne faze g1
(kompozit)" u Pretpostavkama s raspisom tri signala + pobjednik + badge
porijekla (`valuation.params.growth` u exportu).

Distribucija top-15 po prometu: |gap|>30% = 6/15 = 40% (prag 40%, bez
alarma; v3 stanje bilo 33% — pomak od preračuna svih zona s kompozitnim
g1, 18 zona pomaknuto >10%, changelog redovi kind='methodology').
Testovi: tests/test_composite_g1.py (9), tests/test_v31_db.py (3, nad
živom bazom), test_reconcile_v3.py prerađen, test_ttm_growth ažuriran.

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

### R5: sitemap encoding (P3)

Lokalno je `dist/sitemap.xml` čisti, nekomprimirani XML — gzip dodaje
Vercel na serviranju (standardno, s `Content-Encoding: gzip` headerom kad
klijent šalje `Accept-Encoding`). Produkcijska potvrda iz Claude Code
okruženja nije moguća (burzovnilist.com nije na mrežnoj allowlisti; proxy
vraća 403) — provjera za Borisa s vlastitog stroja:
`curl -sI https://burzovnilist.com/sitemap.xml` (Content-Type xml +
eventualni Content-Encoding) i `curl -s --compressed .../sitemap.xml`
(mora vratiti čitljiv XML). Autoritativna potvrda: GSC → Sitemaps status.
Vanjski alat koji prijavljuje "binarni sadržaj" najvjerojatnije ne šalje
Accept-Encoding a dobiva gzip, ili ne dekomprimira — problem alata.

## 2026-07-16 — Metodologija v3, FAZA K: rekalibracija troška kapitala

Temelj: forenzika FAZE D (docs/forenzika_v3_faza_d.md) dokazala da se
rizik zemlje naplaćivao DVAPUT — rf je bio HR 10g (nosi HR spread), a ERP
5,7% je već sadržavao A3 CRP (~1,47 p.b.), skriven umjesto vidljiv.

Promjena (src/params_calibrated.py): r = rf + β×ERP + CRP + nelikvidnost,
gdje je rf = 2,70% (10g Bund, EUR bezrizični, ručni unos 16.07.2026,
exact_unverified), ERP = 4,23% (Damodaran zreli, bez zemlje), CRP = 1,2
p.b. (zaseban, 'A-'/A3 eurozona, strop ≤1,5 p.b., ne množi se betom).
r(β=1): 9,31% → 8,13%. Premija nelikvidnosti nepromijenjena (samo ispod
Z1 praga — potvrđeno da je nijedno likvidno ime nema).

Čuvari (tests/test_r_stack.py): rf < 3,5% (EUR, ne HR krivulja); ERP <
4,5% ("BEZ premije zemlje" u izvoru); 0 < CRP ≤ 1,5 p.b.; r je TOČNO
zbroj vidljivih komponenti; likvidna imena bez premije nelikvidnosti.

UI: kartice "Pretpostavke" sada nose puni raspis — zasebne kartice rf,
ERP i CRP (svaka s izvorom i datumom iza klika) + formula u kartici r.

Učinak na zone (staro→novo, objavljeno kao baza; puni ispis u
scripts/apply_v3_k.py runu; valuation_changelog nosi kind='methodology'
po firmi): 46 zona pomaknuto >10% naviše, 19 nepromijenjeno/malo (comps
i SOTP sidra ne ovise o r). Ključna imena: HT 19,5–27,6 → 22,6–34,1
(raskorak +48,7% → +20,2% iznad); CROS 1.191–1.556 → 1.369–1.874 (+113%
→ +77% iznad); ZABA 19,4–25,8 → 22,9–32,5 (cijena 22,6 sada 1,4% ISPOD
donjeg ruba — kontrola "u zoni ili blizu" prolazi, prati se kroz G/DIV/A);
ATGR 22,1–31,1 → 25,6–38,5; HPB 309,8–431,9 → 360,2–536,6; KOEI 880–925
→ 1.034–1.088. Temperatura tržišta (CROBEX): 16/4/2 → 13/4/5
(iznad/unutar/ispod). NAPOMENA: ovo je 1. od 4 računske faze v3 — TTM i
rast (G), održiva dividenda (DIV) i medijan-sidro (A) tek slijede;
raskoraci se NE fitaju na tržište.

## 2026-07-16 — Metodologija v3, FAZA G: TTM + rast iz podataka + ROE pravilo

Nalaz FAZE D: sve se vrednovalo iz zadnjeg godišnjeg (65 firmi ima
kvartale u bazi), kapitalne metode bez ikakve faze rasta, g1 se uzimao iz
ručnih forward procjena.

Promjene (src/valuation_methods.py build_ctx):
- TTM sloj u data(): flow stavke = FY + YTD interim − YTD lanjski interim
  (ZSE interimi su kumulativni); bilančne stavke = zadnji interim
  (point-in-time). STROGI GATEOVI: q4 kumulativ vs godišnje >5% razlike →
  TTM se NE gradi (nekonzistentna serija, npr. PODR revenue +9,3%); bez
  lanjskog para → godišnje; TTM izvan [0,4×, 2,5×] godišnjeg → godišnje.
  Sve s razlogom u ttm_meta → badge na stranici.
- g1 isključivo iz objavljenih brojki: min(3g CAGR prihoda/zarade, cap
  10%); kratka serija: min(TTM vs zadnje godišnje, cap 8%) + badge. Ručne
  forward procjene UKINUTE za rast (growth_estimates služi još samo
  guidance-DCF FCF proxyju kad CF izvještaj ne postoji). Arhetip
  industrial_forward sada znači "ima izvedenu fazu rasta iz podataka".
- ROE pravilo za opravdani P/B i RI: max(3g medijan godišnjih ROE,
  TTM ROE × 0,9); bez TTM-a godišnji ROE.
- UI badgevi: `TTM podaci (period)`, `godišnji podatak` (s razlogom),
  `kratka serija`, `ROE pravilo` — u karticama pretpostavki.

Čuvari (tests/test_ttm_growth.py, 4 testa): TTM formula neovisno
reproducirana SQL-om (HT); nekonzistentan q4 blokira TTM (PODR); g1 cap i
zabrana forward signala; ROE pravilo.

Učinak (scripts/apply_v3_g.py; valuation_changelog kind='methodology'):
39 zona pomaknuto >10% — u OBA smjera, kako i treba: TTM izbacuje lanjske
jednokratne dobitke (PODR 246–333 → 149–202, sada −9% od sredine — bio
+200% pa −45%; IKBA −21%; VDZG −44%), a diže gdje je ovogodišnja dobit
porasla (INA +51%, AUHR +36%, GARB +20%). ZABA kontrola: +1,3% pomaka
(cijena 2,7% ispod donjeg ruba — "blizu", prati se). Temperatura CROBEX:
13/4/5 → 12/6/4. Top-15 distribucija: i dalje 7/15 s |raskorakom|>30%,
ali SASTAV promijenjen — preostali su upravo slučajevi za faze koje
slijede: ADRS (klase → S), DLKV/RIVP/SPAN/ERNT/HT (dogma jednog sidra →
A; ERNT/HT DCF sidro sada strši NAVIŠE dok potvrdne metode stoje niže —
medijan kvalificiranih metoda u FAZI A to izravnava), CROS (D_sust → DIV).
Raskoraci se NE fitaju na tržište.

## 2026-07-16 — Metodologija v3, FAZA DIV: održiva dividenda (D_sust)

- dividends tablica: payout_type (redovna|jednokratna|iz_zadrzane_dobiti),
  payout_ratio (Σ isplata firme za fiskalnu godinu / NI_parent TE godine;
  NULL s razlogom kad dobiti nema — NIKAD kriva godina), classified_reason.
  Klasifikacija (src/dividend_sustainability.py): EHO formulacija > payout
  >100% (iz zadržane dobiti; CROS FY2023 197%) > 150% medijana prethodnih
  redovnih (HPB 21,83 vs medijan 2,61). 150 isplata klasificirano.
- dividend_policies tablica (mehanizam za ručnu ekstrakciju politika) —
  prazna dok nema izvora u repou/bazi; fallback je medijan (ništa izmišljeno).
- D_sust = održivi payout × normalizirana dobit (TTM feed iz faze G) /
  dionice; payout = politika (ako pokrivena) ili medijan payouta SAMO
  redovnih godina; banke >80% → flag "ovisi o regulatornom odobrenju" +
  baza min(stvarni, 70%) (ZABA: 0,88 → 0,70 uz flag). Pokrivenost najave:
  <1,2 "napeto pokrivena" (HT: 1,13), <1,0 najava se ne koristi.
- DDM SVIH firmi računa nad D_sust — dps ulaz staro→novo: CROS 114,14 →
  116,12 €; ZABA 1,27 → 1,2481 €; HPB 21,83 → POTISNUTO (zadnja isplata
  jednokratna, održiva baza neizračunljiva → DDM se ne računa; sirova
  jednokratna VIŠE NIKAD ne ulazi u model). Zone nepromijenjene (DDM je
  potvrda, ne sidro) — dividendni sanity flag nad D_sust dolazi u FAZI A.
- UI: stranica dionice — "% dobiti" stupac (">100% (iz zadržane dobiti)";
  "—" + tooltip kad dobit godine nije u bazi), badge tipa po retku,
  "Održiva dividenda (procjena)" s punim raspisom iza klika, legenda;
  /dividende — isti stupac + filter po tipu (default sve) + legenda.
- Testovi (tests/test_dividends_sust.py, 5): HPB jednokratna ne diže bazu;
  payout NIKAD prema krivoj godini (sintetički FY1999 → NULL); politika s
  pokrivenošću <1,0 pada na medijan; ZABA regulatorni flag; DDM ulaz =
  D_sust. Playwright: HPB (izvanredna badge, D_sust potisnut), HT (redovne,
  D_sust prikazan), /dividende (stupac, legenda, filter 44→8 redaka).

## 2026-07-16 — Metodologija v3, FAZA A: triangulacija sidra + sanity testovi

- Zona = MEDIJAN kvalificiranih metoda (base>0, conf≥0,5, ne-degenerirane)
  × oblik osjetljivosti primarnog sidra. Kod TOČNO 2 kvalificirane metode
  razmaknute >40% se NE prosječi (v2 §3 duh — KODT slučaj: comps 3× DCF-a
  bi razvukao zonu); sredinu tada nosi sidro. DEMOTE zapis kad ≥2 metode
  konvergiraju ±20% a sidro divergira >30%.
- Test održive dividende (Borisov test, formaliziran; ODLUKA opcija 1):
  prinos iz D_sust na donjem rubu zone ne smije premašiti r − g, gdje je g
  ISTA stopa kojom je zona izračunata (kapitalna sidra 2,5%; DCF/DDM 4%) —
  prag s tuđim g-om lažno bi pobijao zonu. Pad testa → zona "u
  rekalibraciji" (ne objavljuje se kao mjerodavna): trenutačno ATGR, HT,
  QTLG, RIVP, ZB. Obrnuti flag (previsoka uz payout≥90%) analogno.
  ZABA kontrola: PROLAZI (5,4% < 5,8%), zona nepromijenjena.
- Borisov zahtjev: for-dummies blok "Test održive dividende — običnim
  jezikom" na stranici svake dionice gdje je test primjenjiv — 4 kartice
  (D_sust s objašnjenjem kako je izračunata; prinos na donjem rubu s
  brojkama te dionice; prag r−g s Gordonovom logikom; verdikt) + LEGENDA
  POJMOVA dopunjena s 12 pojmova (r, rf, ERP, CRP, TTM, g, g1, CAGR,
  payout, D_sust, "u rekalibraciji", medijan).
- INA-tip (A.4): free float proxy (100 − Σ top-10) < 10% → napomena
  "raskorak nije informativan" + isključenje iz temperature tržišta;
  temperatura sada 4/5/3 uz np=10 (isključeni low-float + rekalibracije) —
  pošteniji, uži agregat.
- CROS acceptance: zona 1.491–2.041 → 1.823–2.496 (medijan DDM 2.762 /
  RI 2.107 / jPB 1.723) — pomiruje metode, znatno bliže DDM-u; raskorak
  +113% (faza D) → +54%. Pomaci >10%: 6 imena (SNBA −75% — medijan od
  {DDM 14, RI 92, jPB 364} legitimno bira srednju; IKBA −17%; ADRS −13%
  prosjek comps+SOTP unutar 40%; KODT +0% zahvaljujući ne-prosječi pravilu).
- Testovi: tests/test_reconcile_v3.py (7 sintetičkih), pytest 66/66;
  Playwright: header + banner + sanity blok + screener oznake + legenda.

## 2026-07-16 — Metodologija v3, FAZA S: klase dionica

- Vrijednost FIRME (klasno agnostična zona iz FAZE A) raspoređuje se na
  klase tržišnim medijanom omjera cijena (src/class_ratio.py): 5 g, samo
  dani kad su OBJE klase trgovane, min N=30; izmjereno: ADRS/ADRS2 1,3953
  (n=354), KODT/KODT2 1,0316 (n=483), CROS/CROS2 1,0394 (n=59); PLAG/PLAG2
  n=0 → teorijski omjer 1,0 + oznaka. Identitet čuvan: Σ klasa = vrijednost
  firme (unit test na ±0,1%).
- Učinak (Borisova ADRS nekonzistentnost riješena): ADRS +78,6% i ADRS2
  +61,2% naspram SVOJIH zona — obje klase konzistentno iznad; razlika
  raskoraka = TOČNO odstupanje današnjeg omjera (1,55) od povijesnog
  medijana (1,40), prikazana činjenica (unit test identiteta). KODT −8,7%
  / KODT2 −10,0%.
- UI: linija "Premija redovne naspram povlaštene: +X% (povijesni tržišni
  medijan — naša raspodjela, ne fundamentalna tvrdnja)" + link na
  Metodologiju; header/graf/screener koriste zonu KLASE.
- Metodologija: sekcija o klasama (zašto premija glasa postoji i zašto se
  ne izvodi teorijski) + priznata greška v3-S.
- pytest 69/69 (3 nova); Playwright: premija vidljiva na ADRS i KODT.

## 2026-07-16 — Metodologija v3, FAZA P: prezentacija, alarmi i bilanca v3

### Changelog v3 po dionici — staro (FAZA D, 16.07. ujutro) → novo (nakon K+G+DIV+A+S)

| Dionica | Stara zona € | Stari raskorak | Nova zona € | Novi raskorak | Status |
|---------|-------------:|---------------:|------------:|--------------:|--------|
| KOEI | 880–925 | +15.2% | 966–1,017 | +4.9% | objavljena |
| KODT | 3,833–4,869 | +3.0% | 4,142–5,668 | -8.7% | objavljena |
| ADRS | 96–101 | +62.6% | 87–92 | +78.6% | objavljena |
| DLKV | 5–6 | +197.4% | 5–7 | +194.3% | low float — raskorak nije informativan |
| ADPL | 21–31 | +18.1% | 29–45 | -16.5% | objavljena |
| HT | 20–28 | +74.2% | — | — | u rekalibraciji (test održive dividende) |
| ZABA | 19–26 | -0.1% | 23–33 | -19.5% | low float — raskorak nije informativan |
| RIVP | 4–6 | +73.7% | — | — | u rekalibraciji (test održive dividende) |
| PODR | 246–333 | -44.8% | 164–222 | -16.9% | objavljena |
| ZITO | 17–23 | -9.0% | 18–25 | -13.0% | objavljena |
| IG | 56–75 | +15.3% | 60–81 | +7.4% | objavljena |
| ERNT | 147–195 | +18.3% | 406–627 | -60.9% | objavljena |
| SPAN | 32–43 | +52.3% | 28–30 | +96.2% | objavljena |
| HPB | 310–432 | -9.9% | 279–416 | -3.9% | low float — raskorak nije informativan |
| ATGR | 22–31 | +90.0% | — | — | u rekalibraciji (test održive dividende) |
| CROS | 1,191–1,556 | +141.7% | 1,825–2,498 | +53.6% | low float — raskorak nije informativan |
| INA | 81–127 | +386.3% | 234–363 | +69.2% | low float — raskorak nije informativan |

*(zone po PRIMARNOJ klasi; klasne zone iz FAZE S; stara mjerenja: docs/forenzika_v3_faza_d.json)*

### Distribucija nakon svega (acceptance 7)

Top-20 likvidnih, kvalificirani (bez low-float i rekalibracija): 4/12 = 33% s |raskorakom| > 30% — ISPOD praga alarma (40%), alarm neaktivan. Preostala velika imena: ADRS +79%, ERNT -61%, SPAN +96%, INGR +493% — svako nosi reverse-DCF implikaciju na svojoj stranici (P.1); ne fitamo na tržište.

### Ostalo u FAZI P

- Reverse-DCF okvir standardiziran: market-implied implikacija ("rast X%/god uz naš r, ili r od Y% uz naš rast") računa se već kod |raskoraka| > 30% i prikazuje u bloku "Što tržišna cijena implicira" na stranici dionice (red rule §8.3 ostaje na 40%).
- Distribucijski alarm: scripts/distribucijski_alarm.py u dnevnom pipelineu; >40% → GitHub issue s labelom calibration-review + automatski banner na /metodologija ("zone u rekalibraciji za dio dionica").
- Priznate greške v3 (sažetak u metodologiji): trailing bez rasta + dvostruko naplaćen rizik zemlje + dogma jednog sidra + sirove dividende + jedna zona za dvije klase → sustavno preniske zone; svaka faza ispravlja jedan uzrok, dokumentirano po dionici.

## 2026-07-16 — Metodologija v3, FAZA SOTP (dodatak): matice s vlastitim biznisom

- INVENTURA komponenti (v_sotp_inputs): ADRS (CROS 67,47% market, MAIS
  93,54% market, Cromaris/HUP/Energetika ebitda_multiple — matica je čisti
  holding, standalone komponenta NIJE potrebna); KOEI (KODT 52,73%, DLKV
  75% market, KPT JV 49%, Novi Siemens JV 60% no_data, standalone); UCG
  (ZABA 96,19% market). Svaka komponenta ima dokumentirano pravilo.
- STANDALONE (t.2): residual_pe aproksimacija iz konsolidiranih UKINUTA —
  standalone se vrednuje iz NEKONSOLIDIRANIH izvještaja (basis='separate';
  NI − prihod od dividendi kćeri) standardnom v3 metodologijom. KOEI GI
  2025 str. 104: nekonsolidirani izvještaji izdani ZASEBNO, nisu lokalno
  → KOEI standalone status "u obradi", vidljivo u UI SOTP raspisu.
  POPIS firmi sa standalone "u obradi": KOEI (jedina).
- JV pravilo (t.3): KPT po knjigovodstvenoj vrijednosti iz bilješke 16
  (44.232 tis. € na 31.12.2025., ručna ekstrakcija iz PDF-a str. 131) uz
  vidljivu napomenu da JV godišnje donosi ~43,6 M€ udjela u dobiti
  (konzervativnost pravila vidljiva); fallback konzervativni P/E×0,80.
- TOPOLOŠKI PRERAČUN (t.4): src/sotp_order.py — kćeri prije matica u
  stage_recompute/stage_regen/apply skriptama; ciklus → CycleError.
- KASKADA (t.5, dopuna forenzike): KOEI raskorak +22,8% = 14,5 p.b.
  UVEZENO (KODT/DLKV) + 8,3 p.b. vlastito (~2/3 uvezeno — hipoteza
  potvrđena); ADRS +101,6% = 24,1 uvezeno + 77,5 vlastito (dominira
  premija na NAV). Dodatak u docs/forenzika_v3_faza_d.md.
- D_sust matice (t.6): pokrivenost najave uključuje priljeve dividendi
  kćeri (zadnja izglasana isplata kćeri × udio), u raspisu.
- Učinak: SAMO KOEI zona 966–1.017 → 825–869 (−14,6%; KPT knjigovodstveno
  + standalone van NAV-a do nekonsolidiranog izvještaja). pytest 75/75.

## 2026-07-16 — FAZA SOTP (nastavak): KOEI nekonsolidirani + automatski dohvat

- src/report_fetch.py: automatski dohvat OBA godišnja izvještaja (kons. +
  NEKONS., PDF, revidirani ima prednost) s EHO feeda za bilo koji ticker;
  uvezano u onboard (stage_filings) — ubuduće se skidaju oba automatski.
  CLI: python -m src.report_fetch <TICKER>.
- KOEI nekonsolidirani FY2025 (revidirani, EHO 16.04.2026.) skinut i RUČNO
  ekstrahiran (bez API-ja, izvori po stranicama): neto dobit Društva
  80.142 tis. € (str. 15), prihod od dividendi Grupe 71.607 tis. €
  (str. 3–4), poslovni prihodi 292.679 tis. € (str. 15), kapital 341.574
  tis. € (str. 16) → filings basis='separate'.
- KOEI standalone AKTIVAN: NI ex-dividende 8.535 tis. € × peer P/E =
  114,9 M€ u NAV-u (umjesto "u obradi"); dvostruko brojanje isključeno
  (71,6 M€ dividendi kćeri izvan standalone dobiti). Popis standalone
  "u obradi": PRAZAN. Zona KOEI nepromijenjena (medijan kvalificiranih
  ostaje na comps 847 €; SOTP interno potpun: 701 € baza).
- pytest 75/75 (test standalone pravila pokriva oba stanja: separate u
  bazi → NEKONSOLIDIRANI raspis; bez njega → "u obradi").
