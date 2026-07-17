"""M37: tab FINANCIJE — as-reported sloj (scripts/build_financije.py).

Acceptance: HRK periodi preračunati fiksnim tečajem (badge na koloni);
restatement (annual vs 4Q kumulativ) prikazuje noviju vrijednost + stariju
iza klika; rupe su null (nikad 0); izvedene veličine (is_reported=false)
NIKAD u tabu. Preskače se bez lokalne baze.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from scripts.build_financije import build_company  # noqa: E402

HRK_EUR = 7.5345


def _connect():
    try:
        import psycopg2

        from src import config
        c = psycopg2.connect(config.dsn())
        with c.cursor() as cur:
            cur.execute("SELECT 1")
        return c
    except Exception:  # noqa: BLE001
        return None


@pytest.fixture()
def conn():
    c = _connect()
    if c is None:
        pytest.skip("lokalna baza nedostupna")
    yield c
    c.rollback()
    c.close()


def _cid(cur, ticker):
    cur.execute("SELECT id, name FROM companies WHERE ticker=%s", (ticker,))
    return cur.fetchone()


def test_hrk_konverzija_fiksnim_tecajem(conn):
    """FY2022 (HRK filing): value_eur == value_raw / 7,5345, a kolona nosi
    hrk=true badge u exportu."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT f.value_raw, f.value_eur FROM financials f
               JOIN filings fl ON fl.id=f.filing_id
               WHERE fl.currency='HRK' AND f.is_reported
                 AND f.value_raw IS NOT NULL AND f.value_eur IS NOT NULL
                 AND ABS(f.value_raw) > 1000 LIMIT 20""")
        rows = cur.fetchall()
    if not rows:
        pytest.skip("nema HRK redova u bazi")
    for raw, eur in rows:
        assert abs(float(raw) / HRK_EUR - float(eur)) < 0.01 * abs(float(eur)), \
            f"HRK konverzija nije fiksni tečaj: raw={raw} eur={eur}"


def test_hrk_badge_na_koloni(conn):
    with conn.cursor() as cur:
        cid, name = _cid(cur, "LPLH")
        data = build_company(cur, cid, "LPLH", name)
    ann = data["views"]["consolidated"]["annual"]
    by_fy = {p["fy"]: p for p in ann["periods"]}
    assert by_fy[2022]["hrk"] is True, "FY2022 mora nositi badge 'preračunato iz HRK'"
    assert by_fy[2025]["hrk"] is False


def test_rupe_su_null_nikad_nula(conn):
    """Stavka bez ekstrahirane vrijednosti mora biti null — u prikazu '—'."""
    with conn.cursor() as cur:
        cid, name = _cid(cur, "LPLH")
        data = build_company(cur, cid, "LPLH", name)
    ann = data["views"]["consolidated"]["annual"]
    n_null = 0
    for st, tbl in ann["statements"].items():
        for r in tbl["rows"]:
            for k, v in r["values"].items():
                assert v is None or isinstance(v, float), f"{st}/{r['item']}/{k}"
                if v is None:
                    n_null += 1
    # LPLH FY2025 nema materijalne troškove ekstrahirane -> bar jedna rupa
    assert n_null >= 1, "očekivana bar jedna null rupa (ne 0!)"


def test_bez_izvedenih_velicina(conn):
    """ebitda/net_debt/total_debt/free_cash_flow (is_reported=false) NIKAD
    u as-reported tabu."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, ticker, name FROM companies WHERE is_live LIMIT 10")
        for cid, ticker, name in cur.fetchall():
            data = build_company(cur, cid, ticker, name)
            if not data:
                continue
            for kinds in data["views"].values():
                for view in kinds.values():
                    for tbl in view["statements"].values():
                        items = {r["item"] for r in tbl["rows"]}
                        assert not items & {"ebitda", "net_debt", "total_debt",
                                            "free_cash_flow"}, \
                            f"{ticker}: izvedena veličina u as-reported tabu"


def test_restatement_sinteticki(conn):
    """Umjetni annual + q4 filing s različitom vrijednošću -> prikazana
    NOVIJA (annual), starija dostupna u restated.prev (badge + klik u UI).
    Sve u transakciji s rollbackom (build_company ne commita)."""
    with conn.cursor() as cur:
        cid, name = _cid(cur, "LPLH")
        vals = {}
        for pt, v in (("annual", 111_000_000.0), ("q4", 100_000_000.0)):
            cur.execute(
                """INSERT INTO filings (company_id, doc_type, fiscal_year,
                     period_type, basis, currency, source_url, published_at)
                   VALUES (%s,'financial_report',1999,%s,'consolidated','EUR',
                           'sintetički-test-m37', %s) RETURNING id""",
                (cid, pt, "2000-04-30" if pt == "annual" else "2000-01-31"))
            fid = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO financials (filing_id, company_id, fiscal_year,
                     period_type, basis, statement, item, value_eur, is_reported)
                   VALUES (%s,%s,1999,%s,'consolidated','income','revenue',%s,true)""",
                (fid, cid, pt, v))
            vals[pt] = v
        data = build_company(cur, cid, "LPLH", name)
        conn.rollback()
    ann = data["views"]["consolidated"]["annual"]
    rev = next(r for r in ann["statements"]["income"]["rows"]
               if r["item"] == "revenue")
    key = "1999-annual"
    assert rev["values"][key] == vals["annual"], "novija (annual) objava pobjeđuje"
    assert rev["restated"][key]["prev"] == vals["q4"], \
        "starija vrijednost mora biti dostupna iza klika"


def test_fin_export_postoji_i_konzistentan():
    """Generirani fin/<T>.json: periodi najnoviji prvi, jedinica definirana."""
    p = pathlib.Path("frontend/public/data/fin/LPLH.json")
    if not p.exists():
        pytest.skip("fin export nije generiran (python -m scripts.build_financije)")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["unit"] in ("mil", "tis"), "svaka kolona mora imati jedinicu"
    ann = d["views"]["consolidated"]["annual"]
    fys = [pp["fy"] for pp in ann["periods"]]
    assert fys == sorted(fys, reverse=True), "najnoviji period mora biti prvi"
    assert all(pp["url"] for pp in ann["periods"]), \
        "svaka kolona mora linkati na izvorni filing"
