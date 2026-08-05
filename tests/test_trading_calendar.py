"""M61: kalendar neradnih dana ZSE — daily-eod ne smije alarmirati na
blagdane (incident 5.8.2026.: Dan pobjede, lažni failure + issue + mail).
Blagdani po Zakonu o blagdanima; pomični iz izračuna Uskrsa."""
from datetime import date

from src.daily import _easter, non_trading_reason


def test_uskrs_poznati_datumi():
    # javno poznati datumi Uskrsa (gregorijanski)
    assert _easter(2024) == date(2024, 3, 31)
    assert _easter(2025) == date(2025, 4, 20)
    assert _easter(2026) == date(2026, 4, 5)


def test_blagdani_2026():
    assert "Dan pobjede" in non_trading_reason(date(2026, 8, 5))
    assert "Uskrsni ponedjeljak" in non_trading_reason(date(2026, 4, 6))
    assert "Tijelovo" in non_trading_reason(date(2026, 6, 4))
    assert "Dan državnosti" in non_trading_reason(date(2025, 5, 30))  # petak
    assert non_trading_reason(date(2026, 1, 1)) is not None
    assert non_trading_reason(date(2026, 12, 25)) is not None


def test_vikend_i_radni_dani():
    assert non_trading_reason(date(2026, 8, 8)) == "vikend"      # subota
    assert non_trading_reason(date(2026, 8, 9)) == "vikend"      # nedjelja
    assert non_trading_reason(date(2026, 8, 4)) is None          # utorak, radni
    assert non_trading_reason(date(2026, 8, 6)) is None          # četvrtak, radni
    assert non_trading_reason(date(2026, 11, 19)) is None        # dan NAKON 18.11.
