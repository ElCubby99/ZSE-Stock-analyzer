"""v3 FAZA SOTP: acceptance 5c — standalone iz nekonsolidiranih izvještaja,
isključenje dividendnog prihoda, JV pravilo, 'u obradi' status.

Sintetički dijelovi rade u transakciji s ROLLBACK-om (baza netaknuta)."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


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


def _koei_sotp(conn):
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx, value_company
    ctx = build_ctx(conn, "KOEI", params=build_params("KOEI"))
    out = value_company(ctx)
    return out["ran"]["sotp_nav"]["range"]


def _insert_separate(conn, fy=2025, ni=60_000_000, div_income=None):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies WHERE ticker='KOEI'")
        cid = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO filings (company_id, fiscal_year, period_type,
                   basis, status, doc_type, source_url)
               VALUES (%s,%s,'annual','separate','parsed','sintetički-test','sintetički-test')
               RETURNING id""",
            (cid, fy))
        fid = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO financials (filing_id, company_id, fiscal_year,
                   period_type, basis, statement, item, value_eur, confidence)
               VALUES (%s,%s,%s,'annual','separate','income',
                       'net_income_parent',%s,0.95)""", (fid, cid, fy, ni))
        if div_income is not None:
            cur.execute(
                """INSERT INTO financials (filing_id, company_id, fiscal_year,
                   period_type, basis, statement, item, value_eur, confidence)
                   VALUES (%s,%s,%s,'annual','separate','income',
                           'dividend_income_from_subsidiaries',%s,0.95)""",
                (fid, cid, fy, div_income))
    return cid


def test_standalone_u_obradi_bez_nekonsolidiranog(conn):
    """KOEI danas: nekonsolidirani izvještaj NIJE u bazi -> standalone
    komponenta 'u obradi', NE aproksimira se iz konsolidiranih (nema
    residual_pe vrijednosti u NAV-u)."""
    vr = _koei_sotp(conn)
    a = vr.assumptions
    assert a.get("standalone_status", {}).get("status") == "u obradi"
    assert not any("residual_pe" in (x.get("basis") or "") for x in a["parts"])
    assert any("U OBRADI" in m for m in a.get("missing", []))


def test_iskljucenje_dividendnog_prihoda_mijenja_zbroj(conn):
    """Acceptance 5c-2: sintetički nekonsolidirani izvještaj — NAV se
    MIJENJA kad se dividendni prihod kćeri isključi."""
    _insert_separate(conn, ni=60_000_000, div_income=None)
    base_bez = _koei_sotp(conn).base
    conn.rollback()
    _insert_separate(conn, ni=60_000_000, div_income=45_000_000)
    base_s_div = _koei_sotp(conn).base
    conn.rollback()
    assert base_bez > base_s_div, (
        "isključenje dividendnog prihoda mora SMANJITI standalone dio "
        f"(bez: {base_bez}, s isključenjem: {base_s_div})")


def test_jv_pravilo_knjigovodstvena_s_izvorom(conn):
    """Acceptance 5c-4: KPT po knjigovodstvenoj vrijednosti iz bilješki,
    s izvorom i pretpostavka badgeom."""
    vr = _koei_sotp(conn)
    kpt = next(x for x in vr.assumptions["parts"] if "KPT" in x["name"])
    assert kpt["placeholder"] is True, "JV pravilo mora nositi pretpostavka badge"
    assert "associate_book" in kpt["basis"]
    assert "bilješka 16" in kpt["basis"]
    assert abs(kpt["value_eur"] - 44_232_000) < 1
