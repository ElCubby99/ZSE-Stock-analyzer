"""M30: auto-generacija vijesti — kandidati imaju ispravan oblik, stabilan
dedup ključ (idempotentnost) i ne uključuju izvedene (NT backfill) dividende.
Radi nad stvarnom lokalnom bazom, read-only."""
import importlib.util
import pathlib
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "generate_news", pathlib.Path("scripts/generate_news.py"))
gn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gn)

LOOKBACK = date.today() - timedelta(days=3650)


def _collect():
    with get_conn() as conn, conn.cursor() as cur:
        return (gn.collect_filing_news(cur, LOOKBACK),
                gn.collect_dividend_news(cur, LOOKBACK))


def test_kandidati_ispravnog_oblika():
    filings, divs = _collect()
    assert filings, "u bazi postoje filingi — kandidata mora biti"
    for it in filings + divs:
        assert set(it) == {"ticker", "category", "headline", "body",
                           "link_path", "auto_source_ref"}
        assert 1 <= len(it["headline"]) <= 120, it["headline"]
        assert it["link_path"].startswith("/dionica/")
        assert it["link_path"] == it["link_path"].lower()
        assert it["body"] is None
    assert all(i["category"] == "novo_izvjesce" and
               i["auto_source_ref"].startswith("filing:") for i in filings)
    assert all(i["category"] == "dividenda" and
               i["auto_source_ref"].startswith("dividend:") for i in divs)


def test_idempotentan_dedup_kljuc():
    """Dva runa nad istim stanjem baze -> identičan skup auto_source_ref
    (server-side unique indeks tada garantira nula duplikata)."""
    f1, d1 = _collect()
    f2, d2 = _collect()
    key = lambda items: sorted(i["auto_source_ref"] for i in items)  # noqa: E731
    assert key(f1) == key(f2)
    assert key(d1) == key(d2)
    assert len(set(key(f1 + d1))) == len(f1) + len(d1), "ref mora biti jedinstven"


def test_izvedene_dividende_iskljucene():
    """NT backfill zapisi (div_type 'izvedeno...') su povijest, ne vijest."""
    _, divs = _collect()
    refs = {int(i["auto_source_ref"].split(":")[1]) for i in divs}
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM dividends WHERE div_type ILIKE '%izvedeno%'")
        derived = {r[0] for r in cur.fetchall()}
    assert derived, "u bazi postoje izvedeni zapisi (Z2)"
    assert not (refs & derived), "izvedene dividende ne smiju u vijesti"
