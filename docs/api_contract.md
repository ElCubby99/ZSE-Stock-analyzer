# API contract — JSON stranice dionice (v2)

Izvor: `python -m src.stock_json <TICKER> [--out dir]` (i `GET /api/dionica/<TICKER>`
u dev modu preko `src/webapi.py`). Statični deploy čita `/data/<TICKER>.json`
(export commitan u `frontend/public/data/`). **Frontend čita isključivo po ovom
ugovoru** — promjena formata = svjesna promjena ovog dokumenta + frontenda.

Opća pravila:
- Broj kojeg nema u bazi je `null` (frontend renderira "—" / "nema u bazi").
  NIKAD 0 kao zamjena i ništa procijenjeno.
- Svaka brojka nosi izvor gdje postoji (`source_page`, `source_url`, `source`,
  `sources` blokovi). Neizvorene pretpostavke nose oznaku (flag/placeholder).
- Iznosi su u EUR (apsolutno); per-share u EUR po dionici; udjeli/stope kao
  decimalni razlomci (0.0931 = 9,31%).
- MAR: JSON sadrži metode/raspone/pretpostavke/činjenice — nikad preporuku.

## Vršna razina

| polje | tip | opis |
|---|---|---|
| ticker, name, sector, is_group, isin | str/bool | iz `companies` (isin null kad su ISIN-i po klasi) |
| fiscal_year | int | zadnja fiskalna godina u bazi (FY0) |
| audited | bool | je li FY0 filing revidiran |
| generated_at | str (ISO date) | datum exporta — baza za `liquidity.days_since_trade` |
| data_status | str | `full` (živa firma) ili `market_only` (izvješća u obradi — objavljuju se SAMO tržišni podaci: cijene, dividende, likvidnost; `valuation`, `financials_3y`, `balance`, `segments`, `ownership`, `bank_kpi` su null, `fundamentals` prazno, uz `data_note` s razlogom) |
| share_classes | list | vidi dolje |
| metrics | obj | eps, bvps, roe, dps, shares_ex_treasury, market_cap_eur, ebitda_eur, per_class[], basis_note |
| fundamentals | list | FY0 stavke: item, label, value_eur, confidence (null = izvedeno), source_page ('computed' = izračun), fiscal_year, source_url, audited, missing |
| prices | list | povijest EOD po klasi: class_ticker, trade_date, close_eur, volume, turnover_eur, source (backfill: zse.hr securityHistory, ~2 g) |
| price_summary | obj | **profil** — vidi dolje |
| dividend_calendar | obj | **profil** — vidi dolje |
| valuation | obj | params (+sources), assumption_flags[], ran[], skipped[], reconciliation, sotp |
| financials_3y | obj | **v2, DIO 1** — vidi dolje |
| balance | obj\|null | **v2, DIO 2** |
| liquidity | obj | **v2, DIO 3** |
| segments | obj\|null | **v2, DIO 4** — null kad segmenata nema (npr. CROS) |
| ownership | obj | **v2, DIO 5** |
| bank_kpi | obj\|null | **M5** — samo za sector='bank', inače null; vidi dolje |
| trend | obj\|null | **M9** — {series[{year, revenue, ebitda, ebitda_margin}], revenue_label, narration, note}; naracija je ČINJENIČNA (brojke + smjer rast/pad/stabilno, bez epiteta); banka: revenue=ukupni operativni prihod; financijski sektor: ebitda=null + n/p u naraciji; godina koje nema → navedena u 'Nedostaje' |
| business_profile | obj\|null | **M9** — {fiscal_year, activity (+activity_source_page), segments[{name, description, source_page}], markets[{market, source_page}], export_share {value, basis, source_page}\|null (samo ako IZRIJEKOM objavljen), issuer_claims[{claim, source_page}] (epiteti = TVRDNJE izdavatelja, citirane; platforma ih ne generira), source, note}; null → 'nema u bazi' |
| mar_note | str | disclaimer |

## share_classes[]
`ticker, class_type ('ordinary'|'preferred'), isin, shares_issued,
treasury_shares, shares_ex_treasury, is_primary, note,
last_price {close_eur, trade_date, volume, source} | null`

## price_summary (profil)
`{as_of, note, classes[]}`; po klasi:
`{class_ticker, last {date, close_eur}, prev_close_eur, change_pct,
high_52w_eur, low_52w_eur, avg_turnover_20d_eur, data_from, note}`.
- `change_pct` je vs prethodni **trgovani** dan (dani bez trgovanja nemaju zapis).
- 52-tjedni raspon računa se samo nad dostupnom poviješću; ako serija počinje
  unutar zadnjih 365 dana, `note` to eksplicitno kaže (npr. TOK — novo uvrštenje).
- `last: null` + note kad klasa nema nijednu cijenu.

## dividend_calendar (profil)
`{as_of, note, upcoming_count, events[]}`; po događaju:
`{class_ticker, fiscal_year, amount_eur, div_type, ex_date, record_date,
payment_date, status, status_hr, source_url}`.
- `status`: `paid` (payment_date ≤ danas) | `upcoming` (izglasana, još nije
  isplaćena) | `proposed` (prijedlog GS — NIJE izglasana).
- Datumi dolaze iz EHO objava; datum koji u objavi ne postoji je `null` —
  ništa se ne izvodi ni ne pogađa.
- `fiscal_year` = godina dobiti iz koje se isplaćuje (konvencija ex-godina − 1,
  vidi src/dividends.py).

## valuation
- `params`: r, g, holding_discount_low/high, peer_pe, peer_pb,
  rates_calibrated, peers_calibrated, `sources` (komponenta → citat/obrazloženje).
- `assumption_flags[]`: {key, label, status='pretpostavka', why} — β uvijek;
  holding diskont i SOTP multiple samo kad je SOTP primjenjiv; peer multipli
  kad nisu kalibrirani (CROS).
- `ran[]`: {key, label, low, base, high, confidence, no_value, assumptions{...}}.
- `skipped[]`: {key, label, reason}.
- `reconciliation`: {zone_low, zone_high, archetype, anchor_methods[],
  method_roles{key → {role: 'anchor'|'anchor_excluded'|'secondary', note,
  vs_zone_pct}}, zone_note, all_methods_low, all_methods_high, dispersion,
  divergent, method_bases{}} | null. **M8**: fer-zona (zone_low–zone_high) je
  raspon SIDRENIH metoda arhetipa (holding → SOTP; banka/osiguranje → RI +
  opravdani P/B; operativne → DCF + multipli), NE min–max svih metoda;
  sekundarne metode ostaju u `ran` s ulogom i razlogom odstupanja; sidro s
  nepozitivnom bazom je isključeno iz zone ('anchor_excluded' + zone_note);
  `dispersion` (i `divergent`) je širina SIDRENE zone — sekundarne leće ne
  vode "razilaze se" naraciju; raspon svih metoda je u `dispersion_all` +
  `all_methods_low/high` (informacija, raskorak ostaje vidljiv).
- `sotp`: {parts[{name, value_eur, basis, pct, placeholder}], net_cash{value_eur,basis},
  net_cash_note, nav_gross_eur, nav_total_eur, holding_discount_range[2],
  holding_discount_reason, market_check{own_market_cap_eur, nav_pre_discount_eur,
  price_vs_nav_pct, note}, missing[]} | null (kad SOTP nije pokrenut).

## financials_3y (DIO 1)
```json
{ "years": [2023, 2024, 2025],
  "rows": [{ "item": "revenue", "label": "Poslovni prihodi",
             "values": {"2023": 447.7e6, "2024": ..., "2025": ...},
             "yoy_pct": 0.123, "cagr_pct": 0.094, "unit": "eur"|"eur_per_share" }],
  "note": "..." }
```
- `years` može imati < 3 unosa (koliko je godina u bazi); vrijednost koje nema
  je `null` (prazan stupanj s oznakom).
- `yoy_pct` = FY0 vs FY-1; `cagr_pct` samo kad postoje pozitivni rubovi niza
  (negativan/nedostajući rub → null, ne besmislica).
- Redovi: revenue, ebitda, ebit, net_income_parent, eps, operating_cf.
  EPS = net_income_parent / kanonski DANAŠNJI broj dionica bez trezorskih.

## balance (DIO 2)
```json
{ "fiscal_year": 2025, "is_financial": false,
  "total_assets": ..., "total_equity": ..., "equity_parent": ..., "bvps": ...,
  "leverage": { "net_debt": ..., "net_debt_to_ebitda": 0.78,
                "current_ratio": null, "current_ratio_note": "...",
                "components_note": "..." } | null,
  "leverage_note": "..." }
```
- **Leverage guard:** `sector ∈ {bank, insurance}` → `leverage = null` +
  `leverage_note` ("n/p — depoziti/pričuve nisu dug"). Frontend prikazuje
  "n/p", NE nulu. Za `holding` leverage postoji, ali `leverage_note` upozorava
  na konsolidiranog osiguratelja.

## liquidity (DIO 3)
```json
{ "as_of": "2026-07-04",
  "thresholds": { "min_turnover_eur": 5000, "stale_days": 5,
                  "very_low_shares": 3, "very_stale_days": 20 },
  "classes": [{ "class_ticker": "ADRS",
                "last_trade": {"date","close_eur","volume","turnover_eur"} | null,
                "days_since_trade": 2 | null,
                "flag": "ok" | "low" | "very_low",
                "note": "zadnja trgovina ..." }],
  "note": "..." }
```
- `last_trade` = zadnji dan s volumenom > 0 u `prices_eod`; `null` znači da u
  dostupnoj povijesti trgovine NEMA → `flag=very_low`, cijena je indikativna.
- `turnover_eur` je STVARNI promet iz tečajnice (prices_eod.turnover_eur) kad
  postoji; fallback je aproksimacija close×volumen (stariji retci bez prometa).
- Pravila: `low` ako promet < min_turnover_eur ILI days > stale_days;
  `very_low` ako volume < very_low_shares ILI days > very_stale_days.
- Frontend MORA prikazati flag uz cijenu u headeru I uz okomite linije cijena
  u verdict spreadu.

## segments (DIO 4) — null kad nema segmenata
```json
{ "fiscal_year": 2025,
  "rows": [{ "key": "tourism", "label": "Turizam", "revenue": ..., "ebitda": ...,
             "net_result": ..., "ebitda_margin": 0.317, "confidence": 0.95,
             "source_page": "..." }],
  "reconciliation": { "revenue_sum", "group_revenue",
                      "revenue_comparable": true|false,
                      "revenue_residual": num|null, "revenue_note": str|null,
                      "ebitda_sum", "group_ebitda", "ebitda_missing_segments": [],
                      "note": "ostatak = eliminacije/centar; ..." } }
```
- Samo OBJAVLJENI IFRS 8 ključevi (tourism/insurance/aquaculture/energy);
  izvedeni interni ključevi (npr. `tourism_hup`, SOTP ulaz) se NE šalju.
- `ebitda`/`margin` = null gdje segment ne objavljuje EBITDA (osiguranje).
- `revenue_comparable=false` kad Σ segmenata uključuje premije osiguranja, a
  kanonski grupni `revenue` ne — tada je `revenue_residual` null i frontend
  prikazuje `revenue_note` (n/p), NE negativan "ostatak" kao eliminacije.

## bank_kpi (M5) — null osim za banke
```json
{ "fiscal_year": 2025,
  "kpis": [{ "key": "roe|roa|nim|cir|cost_of_risk|npl_ratio|npl_coverage|"
                    "cet1_ratio|total_capital_ratio|ldr|loans_yoy|deposits_yoy",
             "label": "...", "unit": "pct", "value": 0.1929 | null,
             "basis": "izvučeno ... | izračun: <formula>", "missing": false }],
  "note": "..." }
```
- 'izvučeno' = objavljena brojka (izvor u `fundamentals`); 'izračun' = formula
  nad izvučenim stavkama (CIR, NIM, LDR, ROE, ROA, YoY — NE prepisuju se).
- Regulatorne stavke bez izvora u dokumentu (npr. CET1 STOPA Grupe kad je
  objavljen samo iznos i RWA) -> value null + missing — dokumentirana rupa,
  nikad izračun "na svoju ruku" u extract sloju.
- Napomena o YoY: FY-1 i FY0 mogu dolaziti iz različitih objava (GFI obrazac
  vs revidirani AR) s različitim definicijama linija.
- Bankovna `fundamentals`/`financials_3y` lista koristi bankovne stavke
  (NII, naknade, rezervacije, krediti, depoziti; regulatorni omjeri s
  unit='pct'); `valuation.ran` za banku uključuje `residual_income`
  (assumptions.equivalence_note objašnjava odnos prema justified_pb_roe).

## ownership (DIO 5)
```json
{ "holders": [{ "name": "Adris grupa d.d.", "ticker": "ADRS", "pct": 0.6747,
                "source": "ADRS AR2025 str 33 (67,47%)" }],
  "known_pct": 0.6747 | null,
  "free_float_pct_approx": 0.3253 | null,
  "note": "free float ≈ 100% − poznati većinski udjeli ...",
  "liquidity_link": "manjinski free float ... plitka knjiga" | null }
```
- Obrnuti `holdings` graf (redovi gdje je `held_company_id` = ova firma).
- Bez zapisanih imatelja → `holders=[]`, `known_pct`/`free_float_pct_approx`
  = null + note (free float se NE procjenjuje).
- `liquidity_link` postoji kad je free float < 40% — tekstualno povezuje
  vlasništvo s oznakom likvidnosti.
