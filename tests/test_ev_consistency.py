"""M45: EV/EBITDA konzistentnost opsega — manjinski udjeli, kratkotrajna
financijska imovina i pridružena društva.

Načelo: konsolidirana EBITDA nosi 100% kćeri -> EV mora sadržavati
manjinske udjele (dodatak), kratkotrajna fin. imovina se odbija kao
de facto gotovina, a pridružena društva (<50%, metoda udjela) se izuzimaju
jer njihova dobit nije u EBITDA. Isti most vrijedi i obrnuto (peer
usporedba: implicirana EV -> vrijednost po dionici).
"""
import sys

import pytest

sys.path.insert(0, ".")

from src.indicators import ev_components  # noqa: E402
from src.valuation_methods import Ctx, Params, compute_comps  # noqa: E402

# KOEI zadnja bilanca (23.07.2026., M€): trž.kap 2.597,8 + dug 54,0 −
# novac 252,4 − kratk. fin. imovina 249,2 + manjinski 240,9 − KPT 44,2
KOEI = dict(mcap=2_597.8e6, td=54.0e6, cash=252.4e6, stfa=249.2e6,
            mi=240.9e6, assoc=44.232e6)


def test_ev_components_koei_minority_dodaje_se():
    """Acceptance 2: EV S manjinskim udjelom je veći TOČNO za iznos MI."""
    with_mi = ev_components(KOEI["mcap"], KOEI["td"], KOEI["cash"],
                            KOEI["stfa"], KOEI["mi"], KOEI["assoc"])
    without_mi = ev_components(KOEI["mcap"], KOEI["td"], KOEI["cash"],
                               KOEI["stfa"], None, KOEI["assoc"])
    assert with_mi - without_mi == pytest.approx(KOEI["mi"])
    # puna vrijednost prema raspisu
    assert with_mi == pytest.approx(2_346.868e6, rel=1e-6)


def test_ev_components_stfa_i_pridruzena_se_odbijaju():
    base = ev_components(1000.0, 100.0, 50.0)
    assert base == 1050.0
    assert ev_components(1000.0, 100.0, 50.0, stfa=30.0) == 1020.0
    assert ev_components(1000.0, 100.0, 50.0, assoc_book=20.0) == 1030.0
    # bez obveznih ulaza nema EV-a (n/p, ne nula)
    assert ev_components(None, 100.0, 50.0) is None
    assert ev_components(1000.0, None, 50.0) is None


def _ctx(vals, holdings=None):
    def data(item):
        v = vals.get(item)
        return (v, 0.9) if v is not None else None
    return Ctx(ticker="TST", sector="industrials", is_group=False,
               holdings=holdings or [], has_segments=False, data=data,
               shares_ex_treasury=1.0, price=10.0, params=Params())


def test_comps_ev_leca_oduzima_manjinski_interes():
    """Most EV -> vrijednost dioničarima u peer usporedbi: uz neto dug se
    oduzima i manjinski interes; bez toga bi firma s konsolidiranom kćeri
    bila precijenjena (multipl × 100% EBITDA, a odbitak samo dug)."""
    base = dict(ebitda=100.0, net_debt=50.0)
    r_no_mi = compute_comps(_ctx(base))
    r_mi = compute_comps(_ctx({**base, "minority_interests": 30.0}))
    v0 = r_no_mi.assumptions["lenses"]["ev_ebitda"]["per_share"]
    v1 = r_mi.assumptions["lenses"]["ev_ebitda"]["per_share"]
    assert v0 - v1 == pytest.approx(30.0, abs=0.01)


def test_comps_ev_leca_nci_iz_razlike_kapitala():
    """Kad stavke manjinskih nema, NCI = total_equity − equity_parent
    (isti fallback kao DCF equity bridge)."""
    base = dict(ebitda=100.0, net_debt=50.0,
                total_equity=500.0, equity_parent=420.0)
    r = compute_comps(_ctx(base))
    assert r.assumptions["ev_bridge"]["nci_eur"] == pytest.approx(80.0)


def test_comps_ev_leca_stfa_i_pridruzena_dodaju_vrijednost():
    """Kratkotrajna fin. imovina (de facto gotovina) i knjigovodstvena
    vrijednost pridruženih društava PRIPADAJU dioničarima — dodaju se u
    mostu (njihova dobit nije u EBITDA pa nisu u multipl × EBITDA)."""
    base = dict(ebitda=100.0, net_debt=50.0)
    hold = [{"held_name": "JV 49%", "ownership_pct": 0.49, "is_insurance": False,
             "jv_book_value_eur": 20.0}]
    r0 = compute_comps(_ctx(base))
    r1 = compute_comps(_ctx({**base, "short_term_fin_assets": 10.0}, hold))
    v0 = r0.assumptions["lenses"]["ev_ebitda"]["per_share"]
    v1 = r1.assumptions["lenses"]["ev_ebitda"]["per_share"]
    assert v1 - v0 == pytest.approx(30.0, abs=0.01)  # +10 STFA +20 pridružena


def test_ebitda_opseg_konsolidiran_za_firme_s_manjinskima():
    """Acceptance 5 (tvrdi test konzistentnosti): za sve firme s ne-nultim
    manjinskim udjelom, EBITDA u bazi dolazi iz KONSOLIDIRANOG izvješća
    (100% kćeri) — standard 'konsolidirano 100% + manjine u EV'. Prorated
    EBITDA bez manjina u EV-u bila bi druga (nekonzistentna) konvencija."""
    from src.db import get_conn
    problems = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT c.ticker FROM financials fin
            JOIN filings f ON f.id = fin.filing_id
            JOIN companies c ON c.id = fin.company_id
            WHERE fin.item='minority_interests' AND fin.value_eur <> 0""")
        tickers = [r[0] for r in cur.fetchall()]
        assert tickers, "u bazi nema firmi s manjinskim udjelima?"
        for t in tickers:
            cur.execute("""
                SELECT f.basis FROM financials fin
                JOIN filings f ON f.id = fin.filing_id
                JOIN companies c ON c.id = fin.company_id
                WHERE c.ticker=%s AND fin.item='ebitda'
                ORDER BY fin.fiscal_year DESC, f.ingested_at DESC LIMIT 1""",
                (t,))
            r = cur.fetchone()
            if r and r[0] != "consolidated":
                problems.append(f"{t}: zadnja EBITDA basis={r[0]}")
    assert not problems, "EBITDA nije konsolidirana za: " + "; ".join(problems)
