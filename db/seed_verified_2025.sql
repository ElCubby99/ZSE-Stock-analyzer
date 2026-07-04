-- ============================================================
--  VERIFICIRANI PODACI (sesija 2026-07-02) — ISIN-ovi i brojevi dionica.
--  Idempotentno. SVAKI redak ima izvor; ništa nije izmišljeno.
--
--  Izvori:
--  [1] Odluke GS Adris grupe 11.06.2026 (PDF s eho.zse.hr, GS-ADRS-b699398c...):
--      "ADRS (ADRS-R-A); ISIN: HRADRSRA0007 / ADRS2 (ADRS-P-A); ISIN: HRADRSPA0009"
--  [2] Odluke GS Croatia osiguranja 09.06.2026 (PDF, GS-CROS-a17063a9...):
--      "CROS / CROS-R-A / HRCROSRA0002 ; CROS2 / CROS-P-A / HRCROSPA0004"
--  [3] Adris godišnje izvješće 2025 (konsolidirano, eho.zse.hr FI-ADRS-8841c8bb...):
--      PDF str 134: temeljni kapital podijeljen na 9.615.900 redovnih i 6.784.100
--      povlaštenih dionica; PDF str 165: na 31.12.2025. trezorske 130.779 (ADRS)
--      i 390.916 (ADRS2); PDF str 165: "MAIS (MAIS-R-A), ISIN: HRMAISRA0007".
--  [4] CROS godišnje izvješće 2025 (konsolidirano, eho.zse.hr FI-CROS-2de1958f...):
--      PDF str 271 (bilješka 22.1): 420.947 redovnih (307.598 I. em. + 113.349
--      II. em., oznaka CROS) i 8.750 povlaštenih (CROS2) = 429.697 dionica;
--      povlaštene su zbog zajamčene dividende klasificirane kao financijska
--      obveza (bilješka 24), ne kapital.
-- ============================================================

-- ADRS klase [1][3]
UPDATE share_classes SET
    isin            = 'HRADRSRA0007',
    shares_issued   = 9615900,
    treasury_shares = 130779
WHERE ticker = 'ADRS';

UPDATE share_classes SET
    isin            = 'HRADRSPA0009',
    shares_issued   = 6784100,
    treasury_shares = 390916
WHERE ticker = 'ADRS2';

-- CROS klase [2][4] — nisu bile u seedu v2. Trezorske nepoznate -> NULL (ne 0,
-- osim gdje izvor ne kaže ništa; ovdje ostavljamo default 0 samo uz oznaku).
INSERT INTO share_classes (company_id, ticker, isin, class_type, shares_issued,
                           has_voting, dividend_note, is_primary_line) VALUES
  ((SELECT id FROM companies WHERE ticker='CROS'), 'CROS',  'HRCROSRA0002', 'ordinary', 420947,
    TRUE,  'redovne (I.+II. emisija)', TRUE),
  ((SELECT id FROM companies WHERE ticker='CROS'), 'CROS2', 'HRCROSPA0004', 'preferred', 8750,
    TRUE,  'povlaštene: 8% zajamčena kumulativna div; klasificirane kao financijska obveza (AR2025 bilj. 22.1/24)', FALSE)
ON CONFLICT (ticker) DO UPDATE SET
    isin = EXCLUDED.isin,
    shares_issued = EXCLUDED.shares_issued,
    dividend_note = EXCLUDED.dividend_note;

-- MAIS ISIN [3] (jedna uvrštena klasa -> companies.isin)
UPDATE companies SET isin = 'HRMAISRA0007' WHERE ticker = 'MAIS';

-- ADRS/CROS companies.isin ostaju NULL: dvije klase s različitim ISIN-ima,
-- ISIN po klasi živi u share_classes (v. gore).

-- ============================================================
--  DOPUNA (sesija 2026-07-02, SOTP korak) — MAIS dionice, vlasnički graf,
--  HUP rezidualna EBITDA. SVAKI redak ima izvor; ništa nije izmišljeno.
--
--  Izvori:
--  [5] Maistra godišnje izvješće 2025 (konsolidirano, eho.zse.hr
--      FI-MAIS-...): PDF str 149: "Temeljni kapital ... podijeljen je na
--      10.944.339 redovnih dionica"; "Društvo ne drži vlastite dionice";
--      "ADRIS GRUPA ... imatelj 10.236.872 redovnih dionica, što predstavlja
--      93,54% temeljnog kapitala". Potvrda broja dionica i na PDF str 224.
--      PDF str 9 (izvješće uprave): konsolidirana EBITDA 88,4 mil EUR.
--  [6] Adris godišnje izvješće 2025: PDF str 33 (bilj. 1, popis ovisnih
--      društava s konačnim % Adrisa kao krajnje matice): MAISTRA 93,54;
--      CROATIA osiguranje 67,47; CROMARIS 100; HUP-ZAGREB 100 (IZRAVNO,
--      nije pod Maistrom — potvrda i PDF str 4 te str 113 u odvojenim
--      izvještajima Društva); energetska društva ZELOVO, VRTAČA,
--      ENCRO VOŠTANE, BABINDUB — SVA 50%.
--      PDF str 89 (bilj. 5): turizam EBITDA iz redovnog poslovanja 111 mil
--      EUR; segment turizma = "Maistra d.d. i povezana društva te
--      HUP-Zagreb d.d." (PDF str 184).
-- ============================================================

-- MAIS klasa [5]: 10.944.339 redovnih, bez vlastitih dionica.
INSERT INTO share_classes (company_id, ticker, isin, class_type, shares_issued,
                           treasury_shares, has_voting, dividend_note, is_primary_line)
VALUES ((SELECT id FROM companies WHERE ticker='MAIS'), 'MAIS', 'HRMAISRA0007',
        'ordinary', 10944339, 0, TRUE,
        'jedina klasa; Društvo ne drži vlastite dionice (AR2025 str 149)', TRUE)
ON CONFLICT (ticker) DO UPDATE SET
    isin = EXCLUDED.isin,
    shares_issued = EXCLUDED.shares_issued,
    treasury_shares = EXCLUDED.treasury_shares,
    dividend_note = EXCLUDED.dividend_note;

-- Vlasnički graf: citati umjesto 'seed/FI2025?' [6].
UPDATE holdings SET source_page = 'ADRS AR2025 str 33 (67,47%)'
WHERE held_name = 'Croatia osiguranje'
  AND parent_company_id = (SELECT id FROM companies WHERE ticker='ADRS');
UPDATE holdings SET source_page = 'ADRS AR2025 str 33 (93,54%); MAIS AR2025 str 149'
WHERE held_name = 'Maistra'
  AND parent_company_id = (SELECT id FROM companies WHERE ticker='ADRS');
UPDATE holdings SET source_page = 'ADRS AR2025 str 33 (100%)'
WHERE held_name = 'Cromaris'
  AND parent_company_id = (SELECT id FROM companies WHERE ticker='ADRS');

-- HUP-Zagreb [6]: izravno 100% Adrisov, NIJE u MAIS konsolidaciji. Segment
-- 'tourism' (111M) uključuje i Maistru koju SOTP vrednuje tržišno -> da se ne
-- broji dvostruko, HUP pokazuje na IZVEDENI ključ 'tourism_hup' (vidi dolje).
UPDATE holdings SET
    segment_key = 'tourism_hup',
    source_page = 'ADRS AR2025 str 4/33/113: HUP-ZAGREB d.d. izravno 100%'
WHERE held_name = 'HUP-Zagreb'
  AND parent_company_id = (SELECT id FROM companies WHERE ticker='ADRS');

-- Energetika [6]: konačni udjel Adrisa u SVIM energetskim društvima je 50%
-- (str 33: ZELOVO 50, VRTAČA 50, ENCRO VOŠTANE 50, BABINDUB 50), a segment
-- EBITDA (12M, bilj. 5) je 100% konsolidirana -> ispravak s krivih 1.0000.
UPDATE holdings SET
    ownership_pct = 0.50,
    source_page = 'ADRS AR2025 str 33: ZELOVO/VRTAČA/ENCRO VOŠTANE/BABINDUB svi 50%'
WHERE held_name = 'Energetika'
  AND parent_company_id = (SELECT id FROM companies WHERE ticker='ADRS');

-- HUP rezidualna EBITDA [5][6] — IZVEDENO (jedina izvedena brojka, jasna
-- aritmetika iz dva citirana izvora, confidence spušten na 0.70):
--   turizam segment (Maistra grupa + HUP) 111,0M [6, str 89, redovno posl.]
--   − Maistra konsolidirana EBITDA 88,4M [5, str 9]  = 22,6M EUR.
-- Ograda: segmentne brojke uključuju unutargrupne odnose (bilj. 5), pa
-- rezidual nosi tu nepreciznost -> needs_review razina pouzdanosti.
-- Uvjetno: no-op dok ADRS FY2025 filing ne postoji (svježi container:
-- prvo ingest extract + segments, ONDA ponovno ovaj seed).
DELETE FROM segment_financials
WHERE segment_key = 'tourism_hup'
  AND company_id = (SELECT id FROM companies WHERE ticker='ADRS')
  AND fiscal_year = 2025;
INSERT INTO segment_financials (filing_id, company_id, fiscal_year, period_type,
                                basis, segment_key, revenue, ebitda, net_result,
                                confidence, source_page)
SELECT f.id, f.company_id, 2025, 'annual', 'consolidated', 'tourism_hup',
       NULL, 22600000, NULL, 0.70,
       'IZVEDENO: bilj.5 str 89 turizam EBITDA (redovna) 111,0M − MAIS AR2025 str 9 kons. EBITDA 88,4M = 22,6M; HUP izravno 100% (str 4/33/113), nije u MAIS konsolidaciji'
FROM filings f
WHERE f.company_id = (SELECT id FROM companies WHERE ticker='ADRS')
  AND f.fiscal_year = 2025 AND f.period_type = 'annual'
  AND f.basis = 'consolidated' AND f.doc_type = 'financial_report';

-- PLAG dionice (sesija 2026-07-03) — PLAG AR2025: str 148 ("2.197.772 redovne
-- dionice ... 420.000 povlaštenih nominalne 33,00 EUR"; "drži 2.346 vlastitih"),
-- str 203 (EPS bilješka: ponderirani broj redovnih bez vlastitih 2.195.426),
-- str 216 (povlaštene 100% Adriatic Investment Group).
-- U share_classes ide SAMO redovna klasa: povlaštene (PLAG2, HRPLAGPA0005)
-- nemaju NIJEDNU tržišnu cijenu (CTLL bez closea) i nose fiksnu dividendu
-- 0,03 EUR/dionici — uključivanje po cijeni redovne napuhalo bi trž.kap ~19%.
INSERT INTO share_classes (company_id, ticker, isin, class_type, shares_issued,
                           treasury_shares, has_voting, dividend_note, is_primary_line)
VALUES ((SELECT id FROM companies WHERE ticker='PLAG'), 'PLAG', 'HRPLAGRA0003',
        'ordinary', 2197772, 2346, TRUE,
        'redovne; povlaštene (420.000, PLAG2) namjerno ISKLJUČENE iz trž.kap — nema cijene, fiksna div 0,03 EUR (AR2025 str 148/203/216)', TRUE)
ON CONFLICT (ticker) DO UPDATE SET
    isin = EXCLUDED.isin,
    shares_issued = EXCLUDED.shares_issued,
    treasury_shares = EXCLUDED.treasury_shares,
    dividend_note = EXCLUDED.dividend_note;

-- ============================================================
--  ZABA (sesija M5) — izvori:
--  [7] ZSE službena tečajnica 02.07.2026: ZABA ISIN HRZABARA0009 (ORD-SHARE).
--  [8] ZABA godišnje izvješće 2025 (ESEF, eho.zse.hr FI-ZABA-...zip),
--      bilješka 31/dionička struktura (podnožje ~str 305-318): "Broj dionica
--      na dan 31. prosinca 320.241.955"; "Trezorske dionice - -" (nema);
--      "UniCredit S.p.A. je izravni vlasnik 308.046.625 dionica Banke ili
--      96,19% u dioničkom kapitalu i glasačkim pravima"; "Banka nema
--      preferencijalnih dionica".
-- ============================================================
INSERT INTO companies (ticker, name, sector, is_group, isin) VALUES
  ('ZABA', 'Zagrebačka banka d.d.', 'bank', TRUE, 'HRZABARA0009')
ON CONFLICT (ticker) DO UPDATE SET sector='bank', isin=EXCLUDED.isin;

INSERT INTO share_classes (company_id, ticker, isin, class_type, shares_issued,
                           treasury_shares, has_voting, dividend_note, is_primary_line)
VALUES ((SELECT id FROM companies WHERE ticker='ZABA'), 'ZABA', 'HRZABARA0009',
        'ordinary', 320241955, 0, TRUE,
        'jedina klasa; bez trezorskih i bez preferencijalnih (AR2025 bilj. 31)', TRUE)
ON CONFLICT (ticker) DO UPDATE SET
    isin = EXCLUDED.isin, shares_issued = EXCLUDED.shares_issued,
    treasury_shares = EXCLUDED.treasury_shares, dividend_note = EXCLUDED.dividend_note;

-- UniCredit S.p.A. (Milano; NIJE na ZSE — u companies samo kao imatelj za
-- vlasnički graf; bez ISIN-a jer se ne prati).
INSERT INTO companies (ticker, name, sector, is_group) VALUES
  ('UCG', 'UniCredit S.p.A. (Milano)', 'bank', TRUE)
ON CONFLICT (ticker) DO NOTHING;

INSERT INTO holdings (parent_company_id, held_company_id, held_name, ownership_pct,
                      listed, valuation_basis, segment_key, default_multiple,
                      is_insurance, as_of, source_page, confidence)
VALUES ((SELECT id FROM companies WHERE ticker='UCG'),
        (SELECT id FROM companies WHERE ticker='ZABA'),
        'Zagrebačka banka', 0.9619, TRUE, 'market', NULL, NULL, FALSE,
        '2025-12-31',
        'ZABA AR2025: UniCredit S.p.A. izravni vlasnik 308.046.625 dionica = 96,19%',
        0.95)
ON CONFLICT (parent_company_id, held_name) DO UPDATE SET
    ownership_pct = EXCLUDED.ownership_pct, source_page = EXCLUDED.source_page;

-- ZITO sektor (M6, ručna odluka korisnika 2026-07-05): operativna prehrambena
-- grupa -> 'consumer' (ne holding; bez SOTP, sa segmentnim prikazom).
UPDATE companies SET sector='consumer', sector_confidence=1.0
WHERE ticker='ZITO';
