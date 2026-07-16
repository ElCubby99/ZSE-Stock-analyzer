"""v3 FAZA DIV: testovi klasifikacije isplata i održive dividende (D_sust).

Acceptance 5/5a/5b iz naloga v3:
  - HPB-tip jednokratna isplata NE podiže održivu bazu;
  - payout se NIKAD ne računa prema pogrešnoj fiskalnoj godini;
  - politika s pokrivenošću < 1,0 pada na medijan;
  - ZABA payout > 80% nosi regulatorni flag;
  - DDM (dps ulaz) računa nad D_sust, nikad nad sirovom jednokratnom.

Sintetički slučajevi rade unutar transakcije s ROLLBACK-om — baza ostaje
netaknuta. Preskaču se bez lokalne baze.
"""
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


def _cid(cur, ticker):
    cur.execute("SELECT id FROM companies WHERE ticker=%s", (ticker,))
    return cur.fetchone()[0]


def test_hpb_jednokratna_ne_dize_bazu(conn):
    """HPB: zadnja isplata (21,83 €) je klasificirana kao jednokratna
    (>150% medijana redovnih) i NE smije postati dps ulaz za DDM."""
    with conn.cursor() as cur:
        cur.execute("""SELECT payout_type FROM dividends d
                       JOIN companies c ON c.id=d.company_id
                       WHERE c.ticker='HPB' AND d.amount_eur=21.83
                         AND d.div_type NOT ILIKE '%rijedlog%'""")
        r = cur.fetchone()
    if not r:
        pytest.skip("HPB 21,83 nije u bazi")
    assert r[0] in ("jednokratna", "iz_zadrzane_dobiti")
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    ctx = build_ctx(conn, "HPB", params=build_params("HPB"))
    dps = ctx.data("dps")
    dh = ctx.dsust_hint or {}
    # ili D_sust (iz redovnih payouta) ili NIŠTA — nikad sirovih 21,83
    if dps is not None and dps[0] is not None:
        assert dps[0] < 21.83 * 0.99, "sirova jednokratna ne smije biti dps"
    else:
        assert dh.get("suppressed_one_off") == 21.83


def test_payout_nikad_prema_krivoj_godini(conn):
    """Sintetička isplata s fiskalnom godinom BEZ dobiti u bazi mora dobiti
    payout_ratio NULL (s razlogom), a NE ratio iz neke druge godine."""
    from src.dividend_sustainability import classify_company
    with conn.cursor() as cur:
        cid = _cid(cur, "HT")
        cur.execute("""SELECT id FROM share_classes WHERE company_id=%s
                       ORDER BY is_primary_line DESC NULLS LAST LIMIT 1""", (cid,))
        scid = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO dividends (company_id, share_class_id, class_ticker,
                   fiscal_year, amount_eur, div_type, source_url)
               VALUES (%s,%s,'HT',1999,0.50,'Izglasana dividenda',
                       'sintetički-test')
               RETURNING id""", (cid, scid))
        div_id = cur.fetchone()[0]
    classify_company(conn, cid)
    with conn.cursor() as cur:
        cur.execute("SELECT payout_ratio, classified_reason FROM dividends WHERE id=%s",
                    (div_id,))
        ratio, reason = cur.fetchone()
    assert ratio is None, "payout prema godini bez dobiti mora biti NULL"
    assert "FY1999" in (reason or "")
    conn.rollback()   # sintetika van; klasifikacije stvarnih redaka su idempotentne


def test_politika_bez_pokrivenosti_pada_na_medijan(conn):
    """Sintetička politika (payout 200%) daje pokrivenost < 1,0 →
    D_sust pada na povijesni medijan, uz vidljivu napomenu."""
    from src.dividend_sustainability import d_sust, ensure_schema
    ensure_schema(conn)
    with conn.cursor() as cur:
        cid = _cid(cur, "HT")
        cur.execute(
            """INSERT INTO dividend_policies (company_id, policy_type, params,
                                              source, extracted_on)
               VALUES (%s,'postotak_dobiti','{"payout": 2.0}'::jsonb,
                       'SINTETIČKI TEST', CURRENT_DATE)
               ON CONFLICT (company_id) DO UPDATE SET params=EXCLUDED.params,
                   source=EXCLUDED.source""", (cid,))
        # NI koji najavu čini nepokrivenom: najava HT ~129M -> NI 100M
        ds = d_sust(conn, cid, 100_000_000.0)
    assert ds is not None
    assert ds["payout_used"] <= 1.0, "politika 200% ne smije proći"
    assert any("medijan" in f or "nije pokrivena" in f for f in ds["flags"]) \
        or "medijan" in ds["payout_basis"]
    conn.rollback()


def test_zaba_regulatorni_flag(conn):
    """ZABA (banka, payout > 80%): flag + baza min(stvarni, 70%)."""
    from src.dividend_sustainability import d_sust
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    ctx = build_ctx(conn, "ZABA", params=build_params("ZABA"))
    ni = ctx.val("net_income_parent")
    with conn.cursor() as cur:
        ds = d_sust(conn, _cid(cur, "ZABA"), ni)
    if ds is None:
        pytest.skip("ZABA bez payout povijesti")
    assert any("regulatornom odobrenju" in f for f in ds["flags"])
    assert ds["payout_used"] <= 0.70 + 1e-9


def test_ddm_ulaz_je_dsust(conn):
    """CROS: dps ulaz mora biti D_sust (payout medijan × NI TTM / dionice),
    ne sirova zadnja isplata."""
    from src.dividend_sustainability import d_sust
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    ctx = build_ctx(conn, "CROS", params=build_params("CROS"))
    dps = ctx.data("dps")
    with conn.cursor() as cur:
        ds = d_sust(conn, _cid(cur, "CROS"), ctx.val("net_income_parent"))
    assert ds is not None and dps is not None
    assert abs(dps[0] - ds["d_sust_ps"]) < 1e-6
