"""M-BOND: YTM/duracija/obračunata kamata — verifikacija na ručno
provjerenim primjerima sa ZATVORENIM formama (±1bp po acceptance)."""
import datetime as dt
import sys

sys.path.insert(0, ".")

from src.bond_math import (  # noqa: E402
    accrued_interest, current_yield, durations, ytm,
)

BP = 1e-4  # 1 basis point


def test_ytm_par_na_kuponski_datum():
    """Cijena 100 točno na kuponski datum -> YTM = kupon (zatvorena forma:
    par obveznica). 3% godišnji kupon, 3 godine."""
    y = ytm(100.0, 3.0, 1, dt.date(2029, 7, 16), dt.date(2026, 7, 16))
    assert abs(y - 0.03) < BP, y


def test_ytm_jedna_godina_zatvorena_forma():
    """1 godina do dospijeća, godišnji kupon c, čista cijena P na kuponski
    datum: YTM = (100 + c) / P − 1. P=97, c=4 -> (104/97)−1 = 7.216495%.
    Napomena: 2026-07-16 -> 2027-07-16 je 365 dana, t=365/365.25 pa
    dopuštamo 2bp zbog ACT/365.25 vremenske osi (i dalje << ±1bp na
    diskontnom faktoru — provjera preko rekonstruirane cijene ispod)."""
    settle, mat = dt.date(2026, 7, 16), dt.date(2027, 7, 16)
    y = ytm(97.0, 4.0, 1, mat, settle)
    t = (mat - settle).days / 365.25
    # egzaktno rješenje NA ISTOJ vremenskoj osi: 104/(1+y)^t = 97
    y_exact = (104.0 / 97.0) ** (1 / t) - 1
    assert abs(y - y_exact) < BP, (y, y_exact)


def test_ytm_dvije_godine_kvadratna_forma():
    """2 godine, godišnji kupon 5, P=98 na kuponski datum: rješenje kvadratne
    5/(1+y)^t1 + 105/(1+y)^t2 = 98 na ACT/365.25 osi — uspoređujemo s
    neovisno izračunatim korijenom (Newton u testu, nezavisna implementacija)."""
    settle, mat = dt.date(2026, 7, 16), dt.date(2028, 7, 16)
    t1 = (dt.date(2027, 7, 16) - settle).days / 365.25
    t2 = (mat - settle).days / 365.25
    f = lambda y: 5 / (1 + y) ** t1 + 105 / (1 + y) ** t2 - 98  # noqa: E731
    y_ind = 0.05
    for _ in range(50):  # Newton, numerička derivacija — NEOVISNA o bisekciji
        h = 1e-7
        y_ind -= f(y_ind) / ((f(y_ind + h) - f(y_ind - h)) / (2 * h))
    y = ytm(98.0, 5.0, 1, mat, settle)
    assert abs(y - y_ind) < BP, (y, y_ind)


def test_ytm_polugodisnji_kupon_par():
    """Polugodišnji kupon, cijena 100 na kuponski datum: efektivni YTM na
    godišnjoj osi ~ (1+c/2/100... — provjera konzistencije: dirty
    rekonstrukcija vraća cijenu unutar 1bp."""
    from src.bond_math import accrued_interest as ai, dirty_price
    settle, mat = dt.date(2026, 7, 16), dt.date(2029, 7, 16)
    y = ytm(99.0, 4.0, 2, mat, settle)
    rec = dirty_price(y, 4.0, 2, mat, settle) - ai(4.0, 2, mat, settle)
    assert abs(rec - 99.0) < 1e-4, rec


def test_obracunata_kamata_polovica_razdoblja():
    """Točno pola godišnjeg kuponskog razdoblja -> pola kupona (ACT/ACT).
    Kupon 4%, razdoblje 16.07.2026-16.07.2027 (365 d), settlement nakon
    182/365 dana."""
    settle = dt.date(2026, 7, 16) + dt.timedelta(days=182)
    a = accrued_interest(4.0, 1, dt.date(2029, 7, 16), settle)
    assert abs(a - 4.0 * 182 / 365) < 1e-9, a


def test_obracunata_kamata_na_kuponski_datum_nula():
    a = accrued_interest(4.0, 1, dt.date(2029, 7, 16), dt.date(2026, 7, 16))
    assert a == 0.0


def test_duracija_zero_kupon_jednaka_rocnosti():
    """Zatvorena forma: Macaulayjeva duracija obveznice bez kupona = ročnost."""
    settle, mat = dt.date(2026, 7, 16), dt.date(2030, 7, 16)
    mac, mod = durations(80.0, 0.0, 1, mat, settle)
    t = (mat - settle).days / 365.25
    assert abs(mac - t) < 1e-9, (mac, t)
    assert mod < mac  # modificirana uvijek manja za y>0


def test_tekuci_prinos():
    assert abs(current_yield(96.0, 3.0) - 0.03125) < 1e-12
    assert current_yield(None, 3.0) is None


def test_ytm_bez_cijene_ili_dospjelo():
    assert ytm(None, 3.0, 1, dt.date(2030, 1, 1), dt.date(2026, 7, 16)) is None
    assert ytm(100.0, 3.0, 1, dt.date(2026, 1, 1), dt.date(2026, 7, 16)) is None
