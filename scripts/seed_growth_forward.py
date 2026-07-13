"""Korak 2 (M13): FORWARD procjena rasta IZ ZADNJEG IZVJEŠĆA — verified seed.

FILOZOFIJA: rast eksplicitne faze (god. 1–5) se NE izvodi iz povijesnog
prosjeka nego iz forward signala u zadnjem godišnjem izvješću (backlog i
njegov trend, book-to-bill, predujmovi/ugovoreno, guidance uprave); trailing
CAGR ostaje samo pomoćni kontekst. Svaka brojka dolje ima IZVOR (dokument +
stranica + citat) — ekstrahirano ručno iz lokalnih PDF-ova (API kredit
nedostupan), po istoj verified-seed politici kao holdings/TOK minority.

PRAVILA IZVOĐENJA (transparentna, konzervativna):
  R1  kvantificiran backlog + book-to-bill > 1:
        g1 = min(ostvareni rast prodaje FY, rast backloga g/g, cap 20%)
      — ograničenje je KAPACITET (ostvareni rast), backlog potvrđuje potražnju.
  R2  samo kvalitativni signali (bez brojčanog backloga):
        g1 = min(ostvareni rast FY / 2, 8%)
      — bez brojčane knjige narudžbi ne ekstrapoliramo dvoznamenkasti rast.
  R3  banka (nema backlog): forward proxy = ostvareni rast dobiti / poslovnih
      prihoda uz izostanak guidance-a; kapitalne metode i dalje koriste
      konzervativni g=2,5% (forward procjena je za NARACIJU i konzistentnost,
      ne za napuhavanje perpetuiteta).

Pokretanje:  python -m scripts.seed_growth_forward
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

DDL = """
CREATE TABLE IF NOT EXISTS growth_estimates (
  id           SERIAL PRIMARY KEY,
  company_id   INT NOT NULL REFERENCES companies(id),
  fiscal_year  INT NOT NULL,
  g1           NUMERIC,
  horizon_years INT DEFAULT 5,
  method       TEXT NOT NULL DEFAULT 'forward_signals',
  rule         TEXT,
  drivers      TEXT,
  basis        TEXT NOT NULL,
  signals      JSONB,
  confidence   NUMERIC,
  source       TEXT,
  created_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE (company_id, fiscal_year, method)
);
"""

SEEDS = [
    {
        "ticker": "KODT", "fy": 2025, "g1": 0.095, "rule": "R1",
        "drivers": "backlog 987,5 M€ (+20,1% g/g), book-to-bill 1,33, prodaja +9,5%",
        "basis": (
            "g1=9,5% = min(ostvareni rast prodaje +9,5%, rast backloga +20,1%, cap 20%) "
            "— R1: kapacitet je ograničenje, backlog pokriva ~1,9 g prihoda i potvrđuje "
            "potražnju. Uprava: 'Visoka razina ugovorenih poslova (backlog) dodatno "
            "osigurava popunjenost proizvodnih kapaciteta i podržava stabilan rast u "
            "narednim godinama' (GI 2025, str. 5). Guidance s brojkama uprava ne daje."),
        "signals": {
            "backlog_eur": 987_499_000, "backlog_yoy": 0.201,
            "backlog_series": {"2022": 288_008_000, "2023": 622_998_000,
                               "2024": 822_423_000, "2025": 987_499_000},
            "book_to_bill": 1.33, "new_orders_eur": 679_797_000,
            "sales_growth_fy": 0.095,
            "quotes": [
                "'Stanje otvorenih obveza, backlog, na kraju 2025. godine veće je za 20% "
                "u odnosu na godinu ranije i iznosi 987,5 milijuna eura' (str. 3)",
                "tablica pokazatelja: Backlog na 31.12. 987.499; Book to bill ratio 1,33 "
                "(str. 4)",
                "'prodaja roba i usluga bilježi rast od 9,5% u odnosu na 2024.' (str. 8)",
            ]},
        "confidence": 0.8,
        "source": "KONČAR-D&ST GI 2025 (data/reports/auto/kodt_2025.pdf), str. 3–5, 8, 10",
    },
    {
        "ticker": "KOEI", "fy": 2025, "g1": 0.20, "rule": "R1",
        "drivers": "backlog 2,7 mlrd € (+31,1% g/g), book-to-bill 1,5, prodaja +25,2%",
        "basis": (
            "g1=20% = min(ostvareni rast prodaje +25,2%, rast backloga +31,1%, CAP 20%) "
            "— R1: backlog pokriva ~2 g prihoda (2,7 mlrd vs 1.320 M€ prodaje). Uprava: "
            "'osigurana stabilna vidljivost prihoda za naredne godine, uz popunjenost "
            "kapaciteta te čvrsta osnova za daljnji rast' (GI 2025, str. 7). Brojčani "
            "guidance uprava ne daje; cap 20% je modelski strop, ne podatak."),
        "signals": {
            "backlog_eur": 2_700_000_000, "backlog_yoy": 0.311,
            "book_to_bill": 1.5, "sales_eur": 1_320_000_000,
            "sales_growth_fy": 0.252,
            "quotes": [
                "'Book-to-bill ratio 1,5; Backlog +31,1%; Prihodi od prodaje +25,2%' "
                "(ključni pokazatelji, str. 4)",
                "'Stanje otvorenih obveza (backlog) na kraju 2025. godine iznosilo je "
                "2,7 milijardi eura...' (str. 7)",
                "'Konsolidirani prihodi od prodaje... 1.320,0 milijuna eura, što je za "
                "265,6 milijuna eura više' (str. 7)",
            ]},
        "confidence": 0.75,
        "source": "Grupa KONČAR kons. GI 2025 (data/reports/auto/koei_2025.pdf), str. 4, 7–9",
    },
    {
        "ticker": "DLKV", "fy": 2025, "g1": 0.08, "rule": "R2",
        "drivers": ("bez brojčanog backloga; prihodi Grupe +43%, uprava očekuje "
                    "'značajnu konjunkturu' (zelena tranzicija)"),
        "basis": (
            "g1=8% = min(ostvareni rast prihoda Grupe +43% / 2, cap 8%) — R2: izvješće "
            "NE objavljuje brojčani backlog pa se dvoznamenkasti rast ne ekstrapolira. "
            "Kvalitativni signali: 'Industriju u kojoj se Dalekovod Grupa natječe "
            "očekuje značajna konjunktura u budućem razdoblju' (str. 8); 'Nastavak "
            "ovakvih pozitivnih trendova očekuje se i u narednom razdoblju' (str. 4); "
            "prihodi vođeni 'visokim stupnjem ugovorenosti poslova' (str. 8). "
            "Brojčani guidance uprava ne daje."),
        "signals": {
            "revenue_eur": 280_004_000, "revenue_growth_fy": 0.43,
            "ebitda_margin": 0.068, "net_fin_debt_eur": -10_268_000,
            "quotes": [
                "'Poslovni prihodi Grupe u 2025. godini iznosili su 280 milijuna eura i "
                "veći su za 43 posto' (str. 6)",
                "'Pozitivni pokazatelji i trendovi oporavka poslovanja predstavljaju "
                "osnovicu za optimističan pogled unaprijed' (str. 6)",
                "segment Energetika +57% (170 M€), Infrastruktura +48% (40 M€) (str. 7)",
            ]},
        "confidence": 0.6,
        "source": "Dalekovod kons. GI 2025 (data/reports/auto/dlkv_2025.pdf), str. 4, 6–8",
    },
    {
        "ticker": "PODR", "fy": 2025, "g1": 0.08, "rule": "R2",
        "drivers": ("završen investicijski ciklus 250 M€ (capex se normalizira), "
                    "akvizicija Agri segmenta (grupa >1 mlrd € prihoda), "
                    "Strategija 2030 — bez brojčanog guidance-a"),
        "basis": (
            "g1=8% (cap R2) — kvalitativni i strukturni signali bez brojčanog "
            "guidance-a: 'početkom 2025. dovršen investicijski ciklus u tehnološku, "
            "logističku i informatičku modernizaciju Prehrane vrijedan 250 milijuna "
            "eura, investicije se u sljedećem petogodišnjem razdoblju planiraju na "
            "uobičajenoj razini' (str. 41) — jednogodišnji FCF FY2025 je zato "
            "potišten izvanrednim capexom; 'Grupa nakon akvizicije premašuje "
            "prihode od milijardu eura' (Agri: Belje, PIK Vinkovci..., str. 40); "
            "Strategija 2030: 'rast temeljen na produktivnosti, inovacijama... "
            "međunarodno širenje' (str. 40). Brojčani guidance uprava ne daje."),
        "signals": {
            "capex_cycle_completed_eur": 250_000_000,
            "agri_acquisition": "Belje, PIK Vinkovci, ... (Fortenova Agri)",
            "group_revenue_post_acq": ">1 mlrd €",
            "planned_agri_capex_2030_eur": 200_000_000,
            "quotes": [
                "'početkom 2025. dovršen investicijski ciklus... 250 milijuna eura, "
                "investicije se u sljedećem petogodišnjem razdoblju planiraju na "
                "uobičajenoj razini' (str. 41)",
                "'Grupa nakon akvizicije premašuje prihode od milijardu eura i ima "
                "gotovo 8.500 zaposlenih' (str. 40)",
                "'Do 2030. planirana su ulaganja od gotovo 200 milijuna eura' u Agri "
                "(str. 42)",
            ]},
        "confidence": 0.6,
        "source": ("Podravka kons. GI 2025 (data/reports/podr_2025_consolidated.pdf), "
                   "str. 14–15, 40–43"),
    },
    {
        "ticker": "ZABA", "fy": 2025, "g1": 0.03, "rule": "R3",
        "drivers": ("banka bez guidance-a: dobit +2,9% uz krediti +16,1% — rast "
                    "dobiti ograničen maržom, ne volumenom"),
        "basis": (
            "g1=3% ≈ ostvareni rast neto dobiti +2,9% (FY2025) — R3: uprava ne daje "
            "guidance; volumen kredita raste +16,1%, ali dobit raste samo +2,9% "
            "(kompresija marže), pa je forward proxy rast DOBITI, ne kredita. "
            "Kapitalne metode (opravdani P/B, RI) i dalje koriste konzervativni "
            "g=2,5% — forward procjena 3% je konzistentna s njim (nešto iznad), "
            "NE ulazi u perpetuitet."),
        "signals": {
            "net_profit_eur": 572_000_000, "profit_growth_fy": 0.029,
            "loans_eur": 15_867_000_000, "loans_growth_fy": 0.161,
            "deposits_growth_fy": 0.043,
            "quotes": [
                "'572 milijun eura dobiti nakon oporezivanja... povećanje od 16 "
                "milijuna (2,9%)' (str. 2)",
                "'Neto krediti i predujmovi komitentima iznose 15.867 milijuna eura. "
                "Povećanje od 2.199 milijuna eura (+16,1%)' (str. 3)",
                "'Depoziti komitenata... 21.646 milijuna eura. Povećanje... (+4,3%)' "
                "(str. 3)",
            ]},
        "confidence": 0.7,
        "source": ("ZABA kons. GI 2025 (data/reports/zaba_2025_consolidated.pdf), "
                   "str. 2–3, 5"),
    },
]


def main() -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        for s in SEEDS:
            cur.execute("SELECT id FROM companies WHERE ticker=%s", (s["ticker"],))
            r = cur.fetchone()
            if not r:
                print(f"[growth] {s['ticker']}: nije u companies — preskačem")
                continue
            cur.execute(
                """INSERT INTO growth_estimates
                       (company_id, fiscal_year, g1, method, rule, drivers, basis,
                        signals, confidence, source)
                   VALUES (%s,%s,%s,'forward_signals',%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (company_id, fiscal_year, method) DO UPDATE SET
                       g1=EXCLUDED.g1, rule=EXCLUDED.rule, drivers=EXCLUDED.drivers,
                       basis=EXCLUDED.basis, signals=EXCLUDED.signals,
                       confidence=EXCLUDED.confidence, source=EXCLUDED.source""",
                (r[0], s["fy"], s["g1"], s["rule"], s["drivers"], s["basis"],
                 json.dumps(s["signals"], ensure_ascii=False), s["confidence"],
                 s["source"]))
            print(f"[growth] {s['ticker']}: g1={s['g1']:.1%} ({s['rule']}) — {s['drivers']}")
        conn.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
