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
