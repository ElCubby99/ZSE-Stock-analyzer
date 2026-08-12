"""M69: klasni pogled za neprimarne klase (povlaštene: CROS2, KODT2, ADRS2,
PLAG2) — vlastita stranica s kompletnim prikazom, top 10 dioničara PO KLASI
i omjerima po cijeni klase. Testovi rade na lokalnoj bazi u transakciji s
rollbackom (seed dioničara je privremen)."""
import datetime
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402
from src.stock_json import _last_dividend, _top10_block, build_stock_json  # noqa: E402


@pytest.fixture()
def conn():
    c = psycopg2.connect(config.dsn())
    c.autocommit = False
    yield c
    c.rollback()
    c.close()


def _company_id(cur, ticker):
    cur.execute("SELECT id FROM companies WHERE ticker=%s", (ticker,))
    return cur.fetchone()[0]


def _seed_shareholders(cur, cid):
    snap = datetime.date(2026, 8, 1)
    rows = [("CROS", 1, "ADRIS GRUPA d.d.", 67.61),
            ("CROS", 2, "REPUBLIKA HRVATSKA", 3.10),
            ("CROS2", 1, "MALI ULAGAČ d.o.o.", 12.00),
            ("CROS2", 2, "DRUGI IMATELJ", 8.00)]
    for ct, rank, name, pct in rows:
        cur.execute(
            """INSERT INTO shareholders (company_id, class_ticker, snapshot_date,
                 source, source_detail, rank, holder_name, pct, is_custody)
               VALUES (%s,%s,%s,'zse_skdd','test',%s,%s,%s,false)""",
            (cid, ct, snap, rank, name, pct))


def test_top10_po_klasi(conn):
    cur = conn.cursor()
    cid = _company_id(cur, "CROS")
    _seed_shareholders(cur, cid)
    ordinary = _top10_block(cur, cid, class_ticker="CROS")
    preferred = _top10_block(cur, cid, class_ticker="CROS2",
                             class_is_primary=False)
    assert [r["name"] for r in ordinary["rows"]] == [
        "ADRIS GRUPA d.d.", "REPUBLIKA HRVATSKA"]
    assert [r["name"] for r in preferred["rows"]] == [
        "MALI ULAGAČ d.o.o.", "DRUGI IMATELJ"]
    # broj dionica izveden iz postotka koristi dionice TE klase
    # (CROS2 ih ima 8750): 12% od 8750 = 1050, ne 12% od svih klasa
    assert preferred["rows"][0]["shares"] == 1050


def test_stari_redovi_bez_klase_pripadaju_primarnoj(conn):
    cur = conn.cursor()
    cid = _company_id(cur, "CROS")
    cur.execute(
        """INSERT INTO shareholders (company_id, class_ticker, snapshot_date,
             source, source_detail, rank, holder_name, pct, is_custody)
           VALUES (%s, NULL, '2026-07-01', 'zse_skdd', 'test-legacy',
                   1, 'LEGACY IMATELJ', 50.0, false)""", (cid,))
    ordinary = _top10_block(cur, cid, class_ticker="CROS")
    preferred = _top10_block(cur, cid, class_ticker="CROS2",
                             class_is_primary=False)
    assert ordinary is not None and ordinary["rows"][0]["name"] == "LEGACY IMATELJ"
    assert preferred is None, "povlaštena NE nasljeđuje redove primarne klase"


def test_dividenda_po_klasi(conn):
    cur = conn.cursor()
    cid = _company_id(cur, "PLAG")
    dps_ord, fy_ord = _last_dividend(cur, cid, class_ticker="PLAG")
    dps_pref, fy_pref = _last_dividend(cur, cid, class_ticker="PLAG2")
    assert fy_ord == fy_pref
    assert dps_ord != dps_pref, "PLAG2 ima vlastiti iznos dividende (15,33 vs 15,30)"


def test_klasni_pogled_cros2(conn):
    d = build_stock_json(conn, "CROS2")
    assert d["ticker"] == "CROS2"
    assert d["view_class"] == {"company_ticker": "CROS", "class_type": "preferred"}
    assert d["isin"] == "HRCROSPA0004"
    flags = {c["ticker"]: c["is_primary"] for c in d["share_classes"]}
    assert flags == {"CROS": False, "CROS2": True}, \
        "klasni pogled okreće is_primary da frontend svugdje gleda klasu"
    # povijest dividendi je za KLASU (CROS2 kroz iste isplate kao CROS)
    hist = (d["dividend_calendar"].get("history") or {}).get("per_year") or []
    assert hist and hist[0]["fiscal_year"] >= 2024
    # per_class omjeri postoje za obje klase (P/E, P/B po cijeni klase)
    tickers = {r["class_ticker"] for r in d["metrics"]["per_class"]}
    assert tickers == {"CROS", "CROS2"}


def test_nepoznat_ticker_i_dalje_pada(conn):
    with pytest.raises(ValueError):
        build_stock_json(conn, "NEPOSTOJI")
