"""M-FOND: matching OMF računa u shareholders + idempotentan uvoz jedinica."""
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402
from src.pension_funds import import_rows, match_omf  # noqa: E402


def test_match_omf_pravila():
    # custodian prefiks + kategorije + ligature (ﬀ)
    assert match_omf("AZ obvezni mirovinski fond kategorije A") == ("AZ", "A")
    assert match_omf("OTP BANKA D.D./ERSTE PLAVI OMF KATEGORIJE B") == ("Erste Plavi", "B")
    assert match_omf("ERSTE & STEIERMARKISCHE BANK D.D./PBZ CO OMF - KATEGORIJA A") == ("PBZ CO", "A")
    assert match_omf("Raiﬀeisen obvezni mirovinski fond kategorije B") == ("Raiffeisen", "B")
    # dobrovoljni fondovi NISU OMF prikaz
    assert match_omf("OTP BANKA D.D./ERSTE PLAVI EXPERT - DOBROVOLJNI MIROVINSKI FOND") is None
    assert match_omf("Raiffeisen dobrovoljni mirovinski fond") is None
    # obični dioničar
    assert match_omf("ADRIS GRUPA d.d.") is None


def test_import_idempotentan():
    conn = psycopg2.connect(config.dsn())
    conn.autocommit = False
    try:
        rows = [{"fund": "AZ", "category": "B",
                 "value_date": "2026-06-30", "unit_value": 123.4567}]
        import datetime as dt
        rows[0]["value_date"] = dt.date(2026, 6, 30)
        n1 = import_rows(conn, rows, "test")
        n2 = import_rows(conn, rows, "test")  # ponovni run: 0 novih
        assert n1 in (0, 1)  # 0 ako je od ranijeg testa
        assert n2 == 0, "ponovljeni uvoz istih podataka ne smije ništa mijenjati"
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fund_units WHERE source='test'")
        conn.commit()
        conn.close()
