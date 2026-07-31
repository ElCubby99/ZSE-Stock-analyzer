"""M53: kurirana pro-forma procjena (BSQR) — regresijski čuvari.

Zona mora dolaziti isključivo iz pro-forma metode (ne iz medijana metoda na
prijavljenim brojkama), hold se skida kad metoda sidri, a objašnjenje metode
(pro_forma_note) mora ići na stranicu.
"""
import pytest

from src.db import get_conn
from src.params_calibrated import build_params
from src.valuation_methods import PRO_FORMA, build_ctx, value_company


@pytest.fixture(scope="module")
def bsqr():
    with get_conn() as conn:
        ctx = build_ctx(conn, "BSQR", params=build_params("BSQR"))
        out = value_company(ctx)
        conn.rollback()
    return out


def test_pro_forma_sidri_bez_holda(bsqr):
    rec = bsqr["reconciliation"]
    assert rec.get("archetype") == "pro_forma"
    assert rec.get("anchor_methods") == ["pro_forma_ev_ebitda"]
    assert rec.get("red_rules") == []          # hold maknut — zona se objavljuje
    assert rec.get("pro_forma_note")           # objašnjenje metode za stranicu


def test_pro_forma_zona_sanity(bsqr):
    rec = bsqr["reconciliation"]
    lo, hi = rec["zone_low"], rec["zone_high"]
    # EBITDA raspon 70,7–95 M€ × peer multipl (~6–10x) − neto dug, × udio
    # matice, na 17,67 M dionica -> zona reda veličine 10–25 €; sve izvan
    # toga znači slomljen ulaz (multipl, dionice, udio matice)
    assert 8 < lo < hi < 30
    assert (hi - lo) / hi > 0.10               # raspon nosi EBITDA raspon


def test_pro_forma_sekundarne_izvan_zone(bsqr):
    roles = bsqr["reconciliation"]["method_roles"]
    assert roles["pro_forma_ev_ebitda"]["role"] == "anchor"
    others = {k: v for k, v in roles.items() if k != "pro_forma_ev_ebitda"}
    assert others, "metode na prijavljenim brojkama moraju ostati prikazane"
    assert all(v["role"] == "secondary" and v["note"] for v in others.values())


def test_pro_forma_izvori_uz_svaku_brojku():
    d = PRO_FORMA["BSQR"]
    for k in ("ebitda_low", "ebitda_high", "net_debt"):
        assert d[f"{k}_eur"] > 0 and d[f"{k}_src"]
    assert 0 < d["parent_share"] < 1 and d["parent_share_src"]
    assert "revidiran" in d["why"] or "NEREVIDIRANO" in d["why"].upper()
