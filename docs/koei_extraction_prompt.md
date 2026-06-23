# Končar — Extraction & Validation Spec (prva Claude Code sesija)

## Cilj sesije
Izgradi pipeline koji iz Končarovih financijskih izvješća (PDF/tekst) puni `financials`
tablicu po `zse_schema.sql`, pa ga dokaži na 3 godine (2023, 2024, 2025) **konsolidirano**.
Bez frontenda. Gotovo kad se izvučene brojke slažu s onim što Boris zna da su točne
i kad sve validacije prolaze.

Napomena o entitetu: Končar je grupa (parent + ovisna društva). Za valuaciju grupe
koristi **konsolidirano**. Standalone (samo matica) ingestaj zasebno, NIKAD ne miješaj
u istom izračunu. Za grupu su ključni `net_income_parent` i `equity_parent`
(jer dio dobiti/kapitala pripada manjinskim udjelima).

---

## KANONSKA TAKSONOMIJA (`item` vrijednosti)
Extractor MORA mapirati na ove ključeve. Sve ostalo ignorira.

**income**
- revenue                       (prihodi od prodaje / poslovni prihodi)
- other_operating_income
- operating_expenses            (ukupni poslovni rashodi, pozitivna magnituda)
- depreciation_amortization     (amortizacija)
- ebit                          (poslovni rezultat; predznak zadržan)
- ebitda                        (ako NIJE objavljen, ostavi null — izračun radi kod: ebit + d&a)
- net_financial_result          (financijski rezultat; predznak)
- pretax_income                 (predznak)
- income_tax                    (porez, pozitivna magnituda)
- net_income                    (ukupna neto dobit grupe; predznak)
- net_income_parent             (pripisano vlasnicima matice; predznak)
- net_income_minority           (pripisano manjinskim udjelima)

**balance**
- total_assets
- total_equity                  (ukupni kapital)
- equity_parent                 (kapital pripisan vlasnicima matice)
- minority_interests
- debt_short                    (kratkoročne kamatonosne obveze)
- debt_long                     (dugoročne kamatonosne obveze)
- cash_and_equivalents
- (net_debt i total_debt NE izvlači — izračun radi kod, is_reported=FALSE)

**cashflow**
- operating_cf                  (novčani tok iz poslovnih aktivnosti)
- capex                         (kapitalna ulaganja / nabava dugotrajne imovine)
- (free_cash_flow = operating_cf - capex; izračun kod)

**shares**
- shares_outstanding            (broj izdanih dionica)
- treasury_shares               (vlastite dionice — bitno, Končar ima buyback)

---

## EXTRACTION SYSTEM PROMPT (za API poziv, model: Opus 4.8)

> Ti si ekstraktor financijskih podataka. Dobivaš tekst jednog financijskog izvješća
> hrvatskog izdavatelja. Vrati ISKLJUČIVO validan JSON po shemi dolje — bez ikakvog
> teksta, objašnjenja ili markdown ograda.
>
> ŽELJEZNA PRAVILA:
> 1. Izvlači SAMO brojke koje su doslovno u dokumentu. Ako stavka ne postoji, stavi
>    null i confidence 0. NIKAD ne procjenjuj, ne izvodi i ne "popunjavaj" brojku.
>    Izmišljena financijska brojka je gora od nedostajuće.
> 2. Odredi metapodatke i budi siguran:
>    - basis: "consolidated" ili "standalone" (traži "konsolidirano"/"nekonsolidirano")
>    - period_type: "annual" | "Q1" | "H1" | "9M"
>    - cumulative: jesu li interim brojke kumulativne (YTD)? IFRS interim obično jest.
>    - audited: revidirano?
>    - currency: "EUR" ili "HRK"
>    - reporting_scale: 1 / 1000 / 1000000 — u kojim su jedinicama brojke iskazane.
>      Traži oznake "u tisućama EUR", "('000)", "u milijunima". OVO JE ČESTA GREŠKA —
>      provjeri zaglavlja tablica, ne pretpostavljaj.
> 3. Predznak: revenue/expenses/imovina/kapital/dug/cash = pozitivna magnituda.
>    Rezultati (ebit, net_financial_result, pretax_income, net_income*) zadrži s
>    predznakom kako su iskazani (gubitak = negativan).
> 4. Za SVAKU stavku navedi source_page (broj stranice ili oznaku bilješke) i
>    confidence 0..1 (koliko si siguran u očitanje i mapiranje).
> 5. Ako naiđeš na "prepravljeno"/"restated"/usporedne brojke za prošlu godinu,
>    izvlači SAMO tekući period ovog izvješća. Prošle periode hvataju njihova izvješća.
>
> IZLAZNA SHEMA:
> {
>   "meta": { "company_ticker": "KOEI", "fiscal_year": 2024, "period_type": "annual",
>             "basis": "consolidated", "cumulative": false, "audited": true,
>             "currency": "EUR", "reporting_scale": 1000 },
>   "items": [
>     { "statement": "income", "item": "revenue", "value_raw": 1234567,
>       "source_page": "str. 12", "confidence": 0.98 },
>     ...
>   ],
>   "flags": [ "tekstualni opis svega sumnjivog/dvosmislenog" ]
> }

---

## VALIDACIJSKI SLOJ (kod, NE LLM) — pokreni nakon svake ekstrakcije
Determinističke provjere. Bilo koja koja padne => filing.status='needs_review', ne ulazi u analitiku.

1. **Bilanca se zatvara:** total_assets ≈ total_equity + (sve obveze). Tolerancija ±0.5%.
   (Ako ne izvlačiš ukupne obveze, barem provjeri total_equity ≤ total_assets.)
2. **Kapital konzistentan:** equity_parent + minority_interests ≈ total_equity (±0.5%).
3. **Dobit konzistentna:** net_income_parent + net_income_minority ≈ net_income (±0.5%).
4. **EBITDA sanity:** ako su ebit i d&a prisutni, ebitda (izvučen ili izračunat) = ebit + d&a.
5. **Scale sanity:** market cap red veličine vs prihod — ako je prihod 1000x premali/prevelik
   od očekivanog, vjerojatno krivi reporting_scale. Flag.
6. **YoY sanity:** bilo koja stavka koja varira >±60% YoY => flag za pregled (ne automatski kriva).
7. **Confidence prag:** bilo koja stavka confidence < 0.85 => needs_review.

Tek kad SVE prođe: filing.status='validated', brojke vidljive analitici.

---

## TIJEK PRVE SESIJE (reci Claude Code-u ovim redom)
1. Pokreni `zse_schema.sql` na lokalnom Postgresu.
2. Napiši loader: tekst izvješća -> API poziv s gornjim promptom -> parsiraj JSON ->
   normaliziraj (value_eur = value_raw * scale; HRK->EUR /7.53450 ako treba) -> insert u `financials`.
3. Napiši validator s 7 pravila gore.
4. Ručno ubaci 3 Končarova konsolidirana godišnja izvješća (2023–2025) i provrti.
5. Ispiši usporednu tablicu (revenue, ebit, ebitda, net_income_parent, equity_parent,
   net_debt, shares) za 3 godine — Boris je očima provjerava protiv stvarnosti.

KPI uspjeha: 3 godine prolaze svih 7 validacija i brojke su točne. Tek tad se skalira.
