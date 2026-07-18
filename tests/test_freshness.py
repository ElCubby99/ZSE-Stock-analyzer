"""M39: brana svježine valuacijskih ulaza.

Invarijanta (Boris): fer vrijednost i svi parametri MORAJU se računati iz
zadnjeg dostupnog izvješća. Test pada ako ijedna live firma ima 'stale_input'
— flow-stavku koju valuacija koristi, a razrješava se na godišnju bazu
STARIJU od zadnjeg godišnjeg filinga (znak da zadnjem izvješću nedostaje ta
stavka pa model tiho pada na stariju godinu).

Test čitanja baze — preskače se ako baza nije dostupna (npr. CI bez ZSE_DSN).
"""
import pytest

try:
    from src.db import get_conn
    from src.freshness import audit_all
    _HAVE_DB = True
except Exception:  # noqa: BLE001
    _HAVE_DB = False


@pytest.fixture(scope="module")
def reports():
    if not _HAVE_DB:
        pytest.skip("baza nedostupna")
    try:
        with get_conn() as conn:
            return audit_all(conn)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"baza nedostupna: {e}")


def test_nijedan_valuacijski_ulaz_nije_zastario(reports):
    """HARD: 0 stale_input — svaka fer vrijednost iz zadnjeg izvješća."""
    stale = [(r["ticker"], f["detail"]) for r in reports
             for f in r["findings"] if f["type"] == "stale_input"]
    assert not stale, (
        "valuacija koristi ZASTARJELE ulaze (nije iz zadnjeg izvješća):\n"
        + "\n".join(f"  {t}: {d}" for t, d in stale))


def test_nepotpuni_zadnji_filinzi_su_poznati(reports):
    """SOFT dokumentacija: incomplete_annual (zadnji godišnji filing bez
    nekog izvještaja) smije postojati samo za poznate, dokumentirane slučajeve
    gdje ta stavka NE ulazi u fer vrijednost (npr. ZITO — comps-sidren, NT
    ne utječe na zonu). Nova pojava izvan popisa = signal za pregled."""
    known = {"ZITO"}   # comps-sidren; NT ne ulazi u fer vrijednost
    incomplete = {r["ticker"] for r in reports
                  for f in r["findings"] if f["type"] == "incomplete_annual"}
    surprise = incomplete - known
    assert not surprise, (
        "nepotpuni zadnji godišnji filinzi izvan poznatih (provjeri utječu li "
        f"na fer vrijednost, pa ekstrahiraj ili dodaj u popis): {sorted(surprise)}")
