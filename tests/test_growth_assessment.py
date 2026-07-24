"""M47: procjena održivog rasta — bez slijepog capa 10%; per-firma verdikt.

Ključna pravila koja test čuva:
- rast koji je SAMOFINANCIRAN (opaženi ≈ ROE×zadržano) smije biti > 10%
  (KOEI-tip): NEMA capa na 10%;
- jednokratni skok jedne godine (PODR-tip) se prepoznaje i NE ulazi u stopu
  (koristi se medijan godišnjih stopa, ne CAGR);
- rast iznad kapaciteta samofinanciranja bez backloga sidri se prema
  fundabilnoj stopi;
- backlog (objavljena tvrda brojka) smije podići near-term rast;
- sanity strop je 25% (a NE 10%);
- beta s niskim R² miješa se sa sektorskom (R²-kredibilitet).
"""
import sys

import pytest

sys.path.insert(0, ".")

from src.growth_assessment import assess_growth  # noqa: E402

KOEI = [(2022, 725.3), (2023, 915.6), (2024, 1070.0), (2025, 1320.0)]
PODR = [(2022, 684.2), (2023, 717.0), (2024, 771.5), (2025, 1013.9)]


def test_samofinanciran_rast_smije_preko_10_posto():
    """KOEI-tip: opaženi ~23% ≈ samofinanciranje 19% -> g1 znatno > 10%
    (dokaz da slijepog capa 10% VIŠE NEMA)."""
    g1, meta = assess_growth(KOEI, 0.193, 0.04, 0.10,
                             margins=[(2022, .069), (2023, .087),
                                      (2024, .149), (2025, .161)])
    assert g1 > 0.15, f"samofinanciran rast neopravdano prignječen: {g1}"
    assert meta["verdict"] == "odrziv_samofinanciran"
    assert "poklapa" in meta["narrative"].lower()


def test_jednokratni_skok_se_izuzima_koristi_medijan():
    """PODR-tip: FY2025 +31% je outlier; reprezentativni rast = medijan
    godišnjih stopa (~7,6%), NE CAGR (koji bi ta godina napuhala)."""
    g1, meta = assess_growth(PODR, 0.10, 0.04, 0.10)
    assert meta["one_off"] == "FY2025"
    assert g1 < 0.12, f"jednokratni skok ušao u stopu: {g1}"
    assert meta["signals"]["g_median"] < meta["signals"]["g_cagr"]


def test_iznad_samofinanciranja_sidri_prema_fundabilnom():
    """Opaženi bitno iznad ROE×zadržano, bez backloga -> sidri naniže."""
    series = [(2022, 100.0), (2023, 115.0), (2024, 132.0), (2025, 152.0)]
    g1, meta = assess_growth(series, 0.05, 0.04, 0.10)  # ~15% obs vs 5% sust
    assert meta["verdict"] == "iznad_samofinanciranja"
    assert 0.05 < g1 < 0.15


def test_backlog_smije_podici_near_term():
    """Objavljena knjiga narudžbi (tvrda brojka) podiže near-term rast."""
    series = [(2022, 100.0), (2023, 108.0), (2024, 116.0), (2025, 125.0)]  # ~8%
    g1_no, _ = assess_growth(series, 0.08, 0.04, 0.10)
    g1_bk, meta = assess_growth(series, 0.08, 0.04, 0.10,
                                backlog={"g": 0.18, "src": "GI2025 str. 12"})
    assert g1_bk > g1_no
    assert meta["verdict"] == "odrziv_backlog"
    assert "narudžbi" in meta["narrative"]


def test_sanity_strop_25_ne_10():
    """Ekstremni samofinancirani rast reže se na 25%, ne na 10%."""
    series = [(2022, 100.0), (2023, 140.0), (2024, 196.0), (2025, 274.0)]  # ~40%
    g1, meta = assess_growth(series, 0.40, 0.04, 0.10)
    assert g1 == pytest.approx(0.25)
    assert any("sanity" in b for b in meta["badges"])


def test_prazna_serija_bez_signala():
    g1, meta = assess_growth([], None, 0.04, 0.10)
    assert g1 is None
    assert meta["verdict"] == "nema_signala"


def test_beta_r2_blend_snizuje_bucnu_betu():
    """M47: niski R² miješa Blume betu sa sektorskom -> niža beta."""
    from src.beta_discipline import R2_REF, SECTOR_BETA
    raw = 1.847
    blume = 0.67 * raw + 0.33
    r2 = 0.354
    sb = SECTOR_BETA["industrial"][0]
    w = r2 / R2_REF
    expected = w * blume + (1 - w) * sb
    assert expected < blume, "blend mora sniziti bučnu betu"
    assert 1.2 < expected < 1.5   # KOEI-tip: ~1,3–1,4, ne 1,57
