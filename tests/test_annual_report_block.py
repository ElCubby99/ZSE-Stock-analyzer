"""M81: blok `annual_report` u snapshotu nikad ne smije tvrditi više nego
što je pročitano.

Runda se vodi o ZADNJEM izvješću. Ako je pročitana pretprošla godina, a
zadnja nije, status 'procitano' bio bi upravo ona lažna sigurnost koja je
16.09.2026. proizvela SNBA incident — zato je tada status 'djelomicno' uz
izričito upozorenje koja godina nije pročitana.

Ne traži mrežu ni bazu: ulazi su zakrpani.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("openpyxl")

from scripts import make_discussion_snapshot as mds  # noqa: E402

XLSX_2024 = "http://x/2024.xlsx"
PDF_2025 = "http://x/2025.pdf"


@pytest.fixture
def stub(monkeypatch):
    """Zakrpa src.report_facts kako ga snapshot uvozi (lokalni import)."""
    import src.report_facts as rf

    state = {"srcs": [], "parsable": set()}

    def annual_sources(cur, ticker, limit=2):
        return list(state["srcs"])

    def fetch(url):
        return b"%PDF-fake" if url.endswith(".pdf") else b"PK-fake-xlsx"

    def facts(blob, *, source_url=None, fiscal_year=None):
        if fiscal_year not in state["parsable"]:
            raise ValueError("nije GFI obrazac (XLSX)")
        return {"consolidated": True, "audited": True, "auditor": "Netko d.o.o.",
                "employees": 10, "subsidiaries": [], "total_assets": None,
                "biggest_moves": []}

    monkeypatch.setattr(rf, "annual_sources", annual_sources)
    monkeypatch.setattr(rf, "fetch", fetch)
    monkeypatch.setattr(rf, "facts", facts)
    monkeypatch.setattr(rf, "kind", lambda b: "pdf" if b.startswith(b"%PDF") else "xlsx")
    monkeypatch.setattr(rf, "text_hints", lambda b: ["stjecanj"])
    monkeypatch.setattr(rf, "text_excerpts", lambda b, limit=4: [])

    class _Cur:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class _Conn(_Cur):
        def cursor(self): return _Cur()

    monkeypatch.setattr("src.db.get_conn", lambda *a, **k: _Conn())
    return state


def test_najnovija_procitana_daje_procitano(stub):
    stub["srcs"] = [(2025, XLSX_2024), (2024, XLSX_2024)]
    stub["parsable"] = {2024, 2025}
    b = mds.annual_report_block("TEST")
    assert b["status"] == "procitano"
    assert "unread" not in b and "upozorenje" not in b


def test_najnovija_neprocitana_nije_procitano(stub):
    """Srž pravila: pročitana 2024. uz nepročitanu 2025. NIJE 'procitano'."""
    stub["srcs"] = [(2025, PDF_2025), (2024, XLSX_2024)]
    stub["parsable"] = {2024}
    b = mds.annual_report_block("TEST")
    assert b["status"] == "djelomicno"
    assert "NAJNOVIJE" in b["upozorenje"] and "2025" in b["upozorenje"]
    assert [u["fiscal_year"] for u in b["unread"]] == [2025]
    assert [y["fiscal_year"] for y in b["years"]] == [2024]


def test_nista_procitano_daje_izricit_status(stub):
    stub["srcs"] = [(2025, PDF_2025), (2024, PDF_2025)]
    stub["parsable"] = set()
    b = mds.annual_report_block("TEST")
    assert b["status"] == "nije_strojno_citljivo"
    assert b["years"] == []
    assert "NAJNOVIJE" in b["upozorenje"]


def test_bez_izvjesca_u_bazi(stub):
    stub["srcs"] = []
    b = mds.annual_report_block("TEST")
    assert b["status"] == "nema_izvjesca"
