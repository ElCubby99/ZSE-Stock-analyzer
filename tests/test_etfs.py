"""M63: čuvari kuriranog ETF registra — imena i indeksi dolaze iz službenih
EHO objava izdavatelja; svaki zapis nosi izvor, ISIN je ICAM-ov, a
index_isin (naš izvor serije) mora postojati u registru ZSE indeksa."""
from src.etfs import CURATED
from src.indices import INDICES

KNOWN_ISINS = {i for _n, (i, _s, _d) in INDICES.items()}


def test_kurirani_zapisi_potpuni():
    assert set(CURATED) >= {"7CRO", "7SLO", "7BET", "7POL", "7CASH", "7GROM"}
    for sym, m in CURATED.items():
        assert m["isin"].startswith("HRICAMF"), f"{sym}: ISIN nije ICAM-ov"
        assert m["name"].startswith("InterCapital"), f"{sym}: ime bez izdavatelja"
        assert "UCITS ETF" in m["name"]
        assert m["index_name"], f"{sym}: nedostaje indeks/košarica koju prati"
        assert m["source"], f"{sym}: zapis bez izvora"


def test_index_isin_postoji_u_registru_indeksa():
    for sym, m in CURATED.items():
        if m["index_isin"] is not None:
            assert m["index_isin"] in KNOWN_ISINS, \
                f"{sym}: index_isin {m['index_isin']} nije u src/indices.py"


def test_7cro_prati_crobex10tr():
    assert CURATED["7CRO"]["index_isin"] == INDICES["CROBEX10tr"][0]


def test_opisi_za_sve_fondove_oba_jezika():
    """M64: SEO opis stranice fonda mora postojati HR+EN za svaki kurirani
    fond (činjenično iz ciljeva fonda u službenim izvještajima)."""
    from src.etfs import DESCRIPTIONS
    for sym in CURATED:
        assert sym in DESCRIPTIONS, f"{sym}: nema opisa"
        assert DESCRIPTIONS[sym].get("hr") and DESCRIPTIONS[sym].get("en"), \
            f"{sym}: opis mora imati OBA jezika"


def test_hr_mjeseci_kompletni():
    from src.etfs import HR_MONTHS
    assert sorted(HR_MONTHS.values()) == list(range(1, 13))
