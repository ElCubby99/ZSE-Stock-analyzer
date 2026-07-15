# ZSE Orchestrator — spec za Claude Code

Cilj: onboardati cijelu burzu **tier po tier** (ne sve odjednom), pa trajno održavati
**jednim dnevnim prolazom**. Dva odvojena posla: ONBOARDING (jednokratno po firmi, bursty)
i WATCHER (dnevno, jeftino). Determinističku pipeline gradi Claude Code; cron je vrti;
API se zove SAMO za klasifikaciju i ekstrakciju. Nema živog agenta u petlji.

---

## 0. Mali schema dodatak (v3)
```sql
ALTER TABLE companies ADD COLUMN tier SMALLINT;                       -- 1 | 2 | 3
ALTER TABLE companies ADD COLUMN onboarding_status TEXT DEFAULT 'discovered';
ALTER TABLE companies ADD COLUMN is_live BOOLEAN DEFAULT FALSE;       -- vidljivo na sajtu?
ALTER TABLE companies ADD COLUMN data_limited BOOLEAN DEFAULT FALSE;  -- tier 3 oznaka na sajtu

CREATE TABLE watcher_state (                 -- kursor: dokle smo stigli na feedu
    source       TEXT PRIMARY KEY,           -- 'zse_disclosure'
    last_seen_id TEXT,
    last_run_at  TIMESTAMPTZ
);

CREATE TABLE pipeline_runs (                  -- log SVAKE akcije -> izvor digesta
    id          BIGSERIAL PRIMARY KEY,
    run_id      TEXT,                         -- jedan noćni run = jedan run_id
    stage       TEXT,                         -- 'watcher'|'extract'|'validate'|'value'|'prices'|'regen'
    company_id  INTEGER REFERENCES companies(id),
    status      TEXT,                         -- 'ok'|'skipped'|'needs_review'|'failed'
    message     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
-- Ekstrakcijski queue NE treba nova tablica: koristi filings.status='pending'.
```

---

## DIO A — TIERED ONBOARDING (jednokratno, sekvencijalno)

### Tieri (svemir u slojevima — ne sve s istim povjerenjem)
- **Tier 1** — CROBEX10 / najlikvidnije (~10). Puna obrada. **Promocija na `live` traži tvoju ručnu potvrdu.**
- **Tier 2** — ostatak CROBEX-a + uređeno tržište s urednim FI (~30–50). Puna pipeline; auto-promocija AKO validacija prođe, inače `needs_review`.
- **Tier 3** — dugi rep / nelikvidni / neredoviti. Best-effort; `data_limited=TRUE`; niska očekivanja.

**Pravilo redoslijeda:** Tier 2 NE počinje dok Tier 1 nije validiran i dok ti očima ne potvrdiš
da pipeline radi. Tier 3 nakon Tier 2. Ovo je svjesni izbor — sprječava 100 tihih krivih firmi odjednom.

### Onboarding state machine (po firmi)
```
discovered -> entity_resolved -> filings_found -> extracting -> validating
           -> [group?] holdings_built -> valued -> (live | needs_review | failed)
```
Gateovi koji NE smiju biti tihi:
1. **entity_resolved** — potvrdi TOČAN izdavatelj (KODT vs KOEI zamka × cijela burza!).
   Za grupe potvrdi konsolidirano. Spremi manifest izvora (URL-ovi izvješća) po firmi.
2. **validating** — 7 pravila iz extraction spec-a. Padne li ijedno -> `needs_review`, NIKAD `live`.
3. **holdings_built** — samo za grupe: izvuci udjele (`ownership_pct` iz bilješki) + segmente.
4. **valued** — pokreni `value_company` (registar metoda); spremi per-metoda + reconciliation.
5. **live** — tek kad validirano. Tier 1 = ručna potvrda; Tier 2/3 = auto ako zeleno.

### Pokretanje
`onboard.py --tier 1` obradi sve firme tog tiera, izvijesti, i STANE. Ti pregledaš,
potvrdiš Tier 1, pa `--tier 2`. Idempotentno: već `live` firme preskače.

---

## DIO B — DNEVNI WATCHER (trajno, jeftino)

**Ne re-scrapeaj svih 100 firmi.** Fundamenti se mijenjaju kvartalno; dnevno skeniranje cijele
baze je besmisleno. Umjesto toga prati JEDAN feed objava.

1. **Povuci** nove objave sa ZSE disclosure feeda OD `watcher_state.last_seen_id` naovamo.
   (~5–30 stavki/dan za cijelu burzu, ne 100 firmi.)
2. **Dedup / idempotencija** — preskoči viđene (UNIQUE na ID objave). Ažuriraj kursor tek na kraju.
3. **Klasificiraj** svaku (Haiku): `financial_report | dividend | gsa | manager_transaction |
   buyback | capital_change | other`. Upiši u `announcements`.
4. **Rutaj:**
   - `financial_report` -> upiši filing `status='pending'` (uđe u ekstrakcijski queue za TU firmu).
   - `dividend` -> ažuriraj `dps`; `buyback`/`capital_change` -> ažuriraj broj dionica/trezorske.
     (Pa recompute ratiose te firme.)
   - `other` -> samo log.
5. **Low-confidence klasifikacija (<0.85)** -> `announcements.needs_review=TRUE`, NE auto-rutaj.

---

## DIO C — DNEVNI RASPORED (redoslijed je bitan)
Od M32: GitHub Actions scheduled workflow (`.github/workflows/daily-eod.yml`,
16:20 Europe/Zagreb radnim danima, nakon zatvaranja ZSE). Jedan `run_id` po prolazu.
```
1. watcher          (feed -> klasifikacija -> rutanje; puni queue, primjenjuje proste update)
2. extract_queue    (SAMO filings status='pending' -> ekstrakcija -> validate gate)
3. recompute        (ratiosi + value_company za POGOĐENE firme; ne sve)
4. prices_eod       (scrape EOD za sve live tickere/klase — jeftino, bez LLM-a)
5. regen            (static regeneracija sajta ako se išta promijenilo)
6. digest           (vidi Dio D)
```
Idempotentno cijelom dužinom: ponovni run je siguran (dedup po ID-evima, transakcija po firmi).

---

## DIO D — ROBUSTNOST + DIGEST (dio koji odlučuje živi li projekt)
Unattended run ĆE udariti promjenu layouta, čudan format, preimenovanu firmu, rate limit, 403.

- **Izolacija greške po firmi:** jedna firma koja padne NE prekida run (try/except po firmi, nastavi).
- **Validacija gate uvijek:** sumnjivo -> `needs_review`, nikad tiho u bazu/na sajt.
- **Retry/resume na scrapeu:** (već imaš `-C` + 4 pokušaja na velikim fajlovima — zadrži).
- **Detekcija promjene layouta:** ako confidence padne na MNOGO firmi isti dan -> alert i
  **pauziraj auto-promociju** (vjerojatno se promijenio format izvora, ne podaci).
- **Dnevni digest tebi** (spoji na postojeći email/morning-brief): obrađeno N objava,
  M novih FI ekstrahirano, K prošlo validaciju, **J u `needs_review` (s linkovima)**, greške,
  ažurirano cijena, status regena. Bez ovog digesta otkriješ za 6 tjedana da 20 firmi ima stare brojke.
  Izvor digesta = `SELECT ... FROM pipeline_runs WHERE run_id = <noćni>`.

---

## GRANICE (NE radi ovo)
- NE re-scrapeaj sve firme dnevno (samo feed + pogođene).
- NE pokreći živog/agentskog Claudea dnevno (determinizam + API samo za klasifikaciju/ekstrakciju).
- NE auto-promoviraj `needs_review`.
- NE daj watcheru da djeluje na low-confidence klasifikaciji.
- NE počinji idući tier dok prethodni nije validiran.
- NE diraj eligibility logiku iz valuation_methods.py.

---

## ŠTO REĆI CLAUDE CODE-U
> "Primijeni v3 schema dodatak. Sagradi `onboard.py` (tiered state machine + gateovi) i `daily.py`
> (Dio C redoslijed). Watcher po Dijelu B, digest po Dijelu D. Sve idempotentno, izolacija greške
> po firmi, validacija gate obavezna. Pokreni `onboard.py --tier 1`, ispiši rezultat po firmi
> (stanje + zašto needs_review gdje je) i STANI — ne diraj Tier 2. Ne mijenjaj eligibility logiku."
```
KPI koraka: Tier 1 (~10 firmi) onboardan, svaka ili `live` ili `needs_review` s jasnim razlogom,
i jedan suhi noćni prolaz koji ti pošalje digest. Tek tad Tier 2.
```

---

## IZMJENA (dogovorena 2026-07-05, prije implementacije)
U onboarding state machine dodan je korak **`sector_assigned`** između
`entity_resolved` i `extracting`:
```
discovered -> entity_resolved -> sector_assigned -> filings_found -> extracting
           -> validating -> [group?] holdings_built -> valued
           -> (live | needs_review | failed)
```
Sektor se dodjeljuje S CONFIDENCEOM prije ekstrakcije jer bira extraction
template (industrijski vs bankovni) i valuacijske metode. Nejasni/dvojni
slučajevi -> `needs_review`, ne pretpostavka. Confidence se sprema u
`companies.sector_confidence` (v3 dodatak).

## IZMJENE 2 (dogovorene 2026-07-05, prije Tiera 2)
1. **ESEF/xhtml ruta je prvorazredna**: kad EHO nudi samo ESEF ZIP, pipeline ga
   raspakira (src/esef.py), parsira xhtml i vodi kroz ISTI validate gate
   (char-window slice, src/auto_slice.build_slice_chars).
2. **Rezolucija broja dionica = zaseban onboarding korak** (`onboard:shares`,
   nakon validacije): share_classes -> ekstrakcija -> fallback službeni ZSE
   listing ("Uvrštena količina" sa stranice papira; trezorske NEPOZNATE -> 0 uz
   ogradu u dividend_note). Bez nazivnika per-share metode ostaju n/p, ne 0.
3. **Promotion gate**: strukturna pravila validacije (1–6) blokiraju uvijek;
   nizak confidence blokira SAMO na JEZGRENIM stavkama. Jezgreni skup
   (eksplicitno, po templateu): nazivnik dionica + {equity_parent|total_equity},
   {net_income_parent|net_income}, {revenue} (banka: {total_operating_income}).
   Sporedne stavke ispod praga se logiraju kao napomena, ne blokiraju.
