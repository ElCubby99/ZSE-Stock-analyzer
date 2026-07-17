# M37 DIO 0 — dijagnostika sheme i pokrivenosti (prije UI-ja)

Datum: 17.07.2026.

## 1. Shema: KANONIZIRANA (mapirana), ne sirovi prijepis

`financials` čuva standardizirane stavke naše sheme ekstrakcije, ne
originalne retke izvještaja:

- **income** (21 stavki): revenue, operating_expenses, material_costs,
  depreciation_amortization, ebit, net_financial_result, interest_expense,
  pretax_income, income_tax, net_income, net_income_parent,
  net_income_minority + bankovne (net_interest_income, net_fee_income,
  total_operating_income, loan_loss_provisions)
- **balance** (18): total_assets, current_assets, inventories,
  trade_receivables, cash_and_equivalents, short_term_fin_assets,
  total_equity, equity_parent, minority_interests, retained_earnings,
  current_liabilities, trade_payables, debt_short, debt_long + bankovne
  (loans_to_customers, deposits_from_customers)
- **cashflow** (5): operating_cf, investing_cf, financing_cf, capex
  (+ free_cash_flow — izveden)

**Posljedica za prikaz**: tab koristi našu kanonsku nomenklaturu s
napomenom "stavke prema standardiziranoj shemi ekstrakcije; originalne
oznake u izvornom dokumentu (link)" — NE tvrdimo doslovni prijepis.

`is_reported=false` označava IZVEDENE veličine (ebitda, total_debt,
net_debt, free_cash_flow — 2.820 redova) → **isključene iz taba**
(pravilo: čisti as-reported sloj; izvedeno ostaje na Ključnim
pokazateljima).

Napomena: 4 male banke (IKBA/KBZ/PDBA/SNBA) imaju legacy statement
naziv 'cash_flow' — alias na 'cashflow' u builderu.

## 2. Pokrivenost (65 live firmi)

- **~50 firmi: puna matrica** — RDG+bilanca+NT godišnje FY2022–FY2025
  (M35 backfill) + ~9 interim perioda (q1/h1/9m/q4 kumulativi).
- Kraće serije: banke IKBA/KBZ/PDBA/SNBA (1 godišnja — FINREP povijest
  nije parsirana), TOK i ZITO (1 g; EHO ima samo PDF/ZIP), IG (2 g),
  CROS/ZABA/HPB/LKRI/ULPL (3 g).
- **Bez godišnjeg NT-a: HPB, ZABA, ZITO** (+ADPL bez FY2025 NT-a);
  interim NT nemaju ni CROS/IKBA/KBZ/KODT/PDBA/SNBA/ZABA → sekcija
  "nije u bazi + link na izvorni dokument".
- Basis: praktički sve konsolidirano; jedini par kons.+nekons. je
  KOEI FY2025 → toggle se prikazuje samo tamo.

## 3. Ostale činjenice bitne za implementaciju

- **Valuta**: `value_eur` je već preračunat pri ingestu (HRK/7,5345 kroz
  normalize); `value_raw` čuva original; `filings.currency` daje badge
  "preračunato iz HRK" (1.681 HRK redova).
- **Restatementi**: 414 stvarnih razlika (>0,5 %) između godišnjeg
  filinga i 4Q kumulativa istog FY-a → godišnja (kasnija/revidirana)
  objava pobjeđuje, badge + starija vrijednost iza klika.
- `filings.published_at` postoji za 679/847 filinga (za redoslijed
  "novija objava pobjeđuje"; fallback: annual > q4 po konvenciji).
- Interim izvještaji su KUMULATIVI od početka godine (TFI konvencija) —
  kvartalni prikaz ih prikazuje kako su objavljeni, uz jasnu oznaku;
  izvedeni diskretni kvartali (razlike kumulativa) NISU u prvoj verziji.
