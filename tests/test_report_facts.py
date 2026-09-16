"""M81: čitanje STVARNOG godišnjeg izvješća (GFI/TFI XLSX s EHO-a).

Incident 16.09.2026. (SNBA): runda je raspravljala o "nerazloženih ~23,5
mil. €" dobiti, a u revidiranom izvješću to je stavka "Ostali prihodi iz
redovnog poslovanja" u godini PRVOG konsolidiranja stečene štedionice.
Ovi testovi brane tri stvari koje su tada zakazale:

  1) oznaka konsolidacije (KD/KN) i ovisni subjekti se čitaju iz obrasca;
  2) stavka s najvećom promjenom se nađe i onda kad je naši agregati ne
     prikazuju;
  3) prijelaz nekonsolidirano -> konsolidirano se PREPOZNA, jer postotna
     usporedba tih dviju godina mjeri različite opsege.

Test gradi minimalni obrazac u memoriji — bez mreže i bez baze.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

openpyxl = pytest.importorskip("openpyxl")

from src import report_facts as rf  # noqa: E402


def _workbook(*, mark: str, auditor: str, employees: int,
              subsidiaries: list[tuple[str, str]], pnl: list[tuple],
              assets: tuple[float, float]):
    """Minimalni GFI obrazac: stupci su [AOP, prethodno, tekuće]."""
    import io
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Opći podaci"
    ws.append(["Tvrtka izdavatelja:", "Test banka d.d."])
    ws.append(["Konsolidirani izvještaj:", mark, "KD/KN"])
    ws.append(["Revidirano:", "RD", "RD/RN"])
    ws.append(["Revizorsko društvo:", auditor])
    ws.append(["Broj zaposlenih (krajem izvještajnog razdoblja):", employees])
    ws.append(["Popis ovisnih subjekata konsolidacije:", "Sjedište"])
    for name, seat in subsidiaries:
        ws.append([name, seat])
    ws.append(["Knjigovodstvo:", "Test"])

    bs = wb.create_sheet("Bilanca")
    bs.append(["Ukupna imovina", 1, assets[0], assets[1]])

    pl = wb.create_sheet("RDG")
    for i, (label, prev, curr) in enumerate(pnl, start=1):
        pl.append([label, i, prev, curr])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


SNBA_2025 = dict(
    mark="KD", auditor="PKF FACT REVIZIJA d.o.o.", employees=299,
    subsidiaries=[("Solvera stambena štedionica d.d.",
                   "Zagreb, Ulica Vjekoslava Heinzela 33A")],
    assets=(292_780_323.0, 612_032_687.0),
    pnl=[("Prihodi na osnovi kamata", 10_869_000.0, 19_524_000.0),
         ("Ostali prihodi iz redovnog poslovanja", 354_572.0, 23_718_896.0),
         ("Opći administrativni rashodi", 8_372_000.0, 15_180_000.0),
         ("Dobit ili gubitak tekuće godine (025 + 028)", 1_005_644.0, 24_142_188.0),
         ("Sitna stavka bez značaja", 1_000.0, 1_200.0)],
)
SNBA_2024 = dict(
    mark="KN", auditor="Moore Audit Croatia d.o.o.", employees=167,
    subsidiaries=[], assets=(234_871_151.0, 292_780_323.0),
    pnl=[("Prihodi na osnovi kamata", 7_431_000.0, 10_869_000.0),
         ("Ostali prihodi iz redovnog poslovanja", 291_000.0, 354_572.0),
         ("Dobit ili gubitak tekuće godine (025 + 028)", 812_000.0, 1_005_644.0)],
)


@pytest.fixture(scope="module")
def curr():
    return rf.facts(_workbook(**SNBA_2025), source_url="http://x/2025.xlsx",
                    fiscal_year=2025)


@pytest.fixture(scope="module")
def prev():
    return rf.facts(_workbook(**SNBA_2024), source_url="http://x/2024.xlsx",
                    fiscal_year=2024)


def test_cita_oznaku_konsolidacije_i_reviziju(curr, prev):
    assert curr["consolidated"] is True and curr["consolidated_mark"] == "KD"
    assert prev["consolidated"] is False and prev["consolidated_mark"] == "KN"
    assert curr["audited"] is True
    assert curr["auditor"] == "PKF FACT REVIZIJA d.o.o."


def test_cita_ovisne_subjekte_i_zaposlene(curr, prev):
    assert [s["name"] for s in curr["subsidiaries"]] == \
        ["Solvera stambena štedionica d.d."]
    assert curr["subsidiaries"][0]["seat"].startswith("Zagreb")
    assert prev["subsidiaries"] == []
    assert (prev["employees"], curr["employees"]) == (167, 299)


def test_ukupna_imovina_uzima_zadnje_dvije_brojke(curr):
    assert curr["total_assets"] == {"prev": 292_780_323.0, "curr": 612_032_687.0}


def test_najveca_promjena_je_stavka_koja_objasnjava_skok(curr):
    """Ono što naši agregati ne pokazuju, izvješće pokazuje po imenu."""
    ostali = curr["biggest_moves"][0]
    assert ostali["label"].startswith("Ostali prihodi")
    assert ostali["delta"] == pytest.approx(23_364_324.0)
    dobit = next(r for r in curr["biggest_moves"]
                 if r["label"].startswith("Dobit ili gubitak tekuće godine"))
    # skok "ostalih prihoda" pokriva gotovo cijeli rast dobiti — upravo to
    # agenti nisu vidjeli jer u našim agregatima te stavke nema
    assert ostali["delta"] / dobit["delta"] > 0.99


def test_sitne_stavke_ne_ulaze_u_najvece_promjene(curr):
    assert not any(r["label"].startswith("Sitna stavka")
                   for r in curr["biggest_moves"])


def test_watch_stavke_uvijek_izvucene(curr):
    labels = {r["label"] for r in curr["watch"]}
    assert any(l.startswith("Ostali prihodi") for l in labels)
    assert any(l.startswith("Opći administrativni") for l in labels)
    assert any(l.startswith("Prihodi na osnovi kamata") for l in labels)


def test_promjena_opsega_se_prepoznaje(curr, prev):
    assert rf.consolidation_changed(prev, curr) is True
    assert rf.consolidation_changed(curr, curr) is False


def test_nepoznata_oznaka_ne_postaje_false():
    """'Ništa izmišljeno': neprepoznata oznaka je None, a None NIJE promjena."""
    f = rf.facts(_workbook(**{**SNBA_2025, "mark": ""}))
    assert f["consolidated"] is None
    assert rf.consolidation_changed(f, f) is False


def _zip(members: dict[str, bytes]) -> bytes:
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_prepoznaje_format_preuzetog_dokumenta():
    xlsx = _workbook(**SNBA_2025)
    assert rf.kind(xlsx) == "xlsx"
    assert rf.kind(b"%PDF-1.7 ...") == "pdf"
    assert rf.kind(b"nista od ovoga") == "nepoznato"
    esef = _zip({"r/izvjesce.xhtml": "<html>tekst</html>".encode()})
    assert rf.kind(esef) == "esef"


def test_gfi_obrazac_u_zip_omotu_se_procita():
    """HT 2025.: EHO pod istim tipom nudi zip, ne obrazac — ako je obrazac
    unutra, čita se; ako nije, čitanje pada s jasnim razlogom, ne KeyErrorom."""
    wrapped = _zip({"paket/GFI.xlsx": _workbook(**SNBA_2025)})
    f = rf.facts(wrapped)
    assert f["consolidated_mark"] == "KD"

    nested = _zip({"vanjski/unutarnji.zip": wrapped})
    assert rf.facts(nested)["employees"] == 299

    esef = _zip({"r/izvjesce.xhtml": b"<html></html>"})
    with pytest.raises(ValueError, match="nije GFI obrazac"):
        rf.facts(esef)


def test_esef_paket_se_barem_pretrazi_na_naznake():
    """Nepročitano se ne prešućuje — iz teksta se izvuku naznake za čovjeka."""
    inner = _zip({"r/izvjesce.xhtml":
                  "Društvo je u 2025. provelo PRIPAJANJE ovisnog društva.".encode()})
    assert rf.text_hints(inner) == ["ovisnog društva", "pripajanj"]
    assert rf.text_hints(_zip({"v/u.zip": inner})) == ["ovisnog društva", "pripajanj"]
    assert rf.text_hints(b"nije ni pdf ni zip") == []


def test_izvodi_se_ne_vade_iz_necega_sto_nije_pdf():
    """Izvodi su PDF-specifični; za obrazac i ESEF vraća prazno, ne izmišlja."""
    assert rf.text_excerpts(_workbook(**SNBA_2025)) == []
    assert rf.text_excerpts(_zip({"r/a.xhtml": b"povoljne kupnje"})) == []


def test_uzi_popis_naznaka_izostavlja_sum():
    """'konsolidir' stoji na svakoj drugoj stranici grupnog izvješća i ne
    znači jednokratni učinak — zato nije u užem popisu."""
    assert "konsolidir" in rf.PDF_HINTS
    assert "konsolidir" not in rf.ONE_OFF_HINTS
    assert set(rf.ONE_OFF_HINTS) <= set(rf.PDF_HINTS) | {"prvi put konsolidir"}
    # slaba naznaka se pojavljuje i u računovodstvenim politikama
    assert "poslovno spajanje" in rf.WEAK_HINTS
    assert "povoljne kupnje" in rf.STRONG_HINTS
    assert not set(rf.STRONG_HINTS) & set(rf.WEAK_HINTS)


def test_jaka_naznaka_istiskuje_sablonu_iz_politika(monkeypatch):
    """ADRS2: šablona 'ako je poslovno spajanje ostvareno u etapama…' sa
    42. stranice ne smije istisnuti stvarni nalaz s 274."""
    stranice = ["nebitno"] * 300
    stranice[41] = "Ako je poslovno spajanje ostvareno u etapama, knjigovodstvena vrijednost…"
    stranice[273] = "…priznavanju dobiti od povoljne kupnje u iznosu od 57.531 tisuću eura."
    _patch_pdf(monkeypatch, stranice)

    ex = rf.text_excerpts(b"%PDF-fake")
    assert [e["stranica"] for e in ex] == [274]
    assert "57.531" in ex[0]["izvod"]


def test_slaba_naznaka_se_vrati_kad_jake_nema(monkeypatch):
    """Šutnja nije opcija: ako jake naznake nema, vraća se slaba."""
    stranice = ["nebitno"] * 60
    stranice[41] = "Ako je poslovno spajanje ostvareno u etapama…"
    _patch_pdf(monkeypatch, stranice)

    ex = rf.text_excerpts(b"%PDF-fake")
    assert [e["stranica"] for e in ex] == [42]


def _patch_pdf(monkeypatch, stranice):
    class _Page:
        def __init__(self, t): self._t = t
        def get_text(self): return self._t

    class _Doc:
        def __init__(self, ps): self._ps = [_Page(t) for t in ps]
        def __iter__(self): return iter(self._ps)
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(rf, "kind", lambda b: "pdf")
    monkeypatch.setattr(rf, "_pdf_open", lambda b: _Doc(stranice))


def test_obrazac_bez_listova_ne_puca():
    import io
    wb = openpyxl.Workbook()
    wb.active.title = "Nesto drugo"
    buf = io.BytesIO()
    wb.save(buf)
    f = rf.facts(buf.getvalue())
    assert f["consolidated"] is None and f["total_assets"] is None
    assert f["watch"] == [] and f["biggest_moves"] == []


class _FakeCur:
    """Minimalni kursor: bilježi SQL i parametre, vraća zadani rezultat."""

    def __init__(self, rows):
        self.rows, self.sql, self.params = rows, None, None

    def execute(self, sql, params=None):
        self.sql, self.params = sql, params

    def fetchall(self):
        return self.rows


def test_klasa_dionice_se_razrjesava_na_firmu():
    """ADRS2/CROS2/KODT2/PLAG2 su oznake KLASE; izvješće podnosi firma.
    Prije popravka je revizija za ADRS2 javljala 'nema izvješća' iako
    izvješće postoji — lažna praznina je jednako opasna kao lažna brojka."""
    cur = _FakeCur([(2025, "http://x/2025.pdf"), (2024, "http://x/2024.xlsx")])
    out = rf.annual_sources(cur, "ADRS2")

    assert out == [(2025, "http://x/2025.pdf"), (2024, "http://x/2024.xlsx")]
    assert "share_classes" in cur.sql, "klasa se mora razriješiti preko share_classes"
    assert cur.params == ("ADRS2", "ADRS2")


def test_unutar_godine_xlsx_ima_prednost_pred_pdf():
    """Obrazac je strojno čitljiv, PDF nije — redoslijed odlučuje SQL, a
    ovdje se brani da se za istu godinu uzme PRVI (dakle bolji) zapis."""
    cur = _FakeCur([(2025, "http://x/a.xlsx"), (2025, "http://x/a.pdf"),
                    (2024, "http://x/b.xlsx")])
    assert rf.annual_sources(cur, "TEST") == [(2025, "http://x/a.xlsx"),
                                              (2024, "http://x/b.xlsx")]


def test_limit_vraca_zadnje_dvije_godine():
    cur = _FakeCur([(2025, "a"), (2024, "b"), (2023, "c")])
    assert [fy for fy, _ in rf.annual_sources(cur, "TEST")] == [2025, 2024]
    assert [fy for fy, _ in rf.annual_sources(cur, "TEST", limit=3)] == [2025, 2024, 2023]
