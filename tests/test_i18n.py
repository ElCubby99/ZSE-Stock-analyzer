"""M38: i18n testovi — hreflang reciprocitet, centralno formatiranje po
jeziku, lint hardkodiranih stringova, glosar.

Pravilo (CLAUDE.md): svaki novi user-facing string ide kroz i18n rječnik;
svaka nova ruta registrira HR i EN par u registryju; PR koji doda
hardkodirani string ili rutu bez para ne prolazi.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend"
DIST = FRONT / "dist"
SITE = "https://www.burzovnilist.com"

# Komponente POTPUNO konvertirane na i18n rječnik (t()) — lint ih čuva.
# Svaka novokonvertirana komponenta se DODAJE ovdje; cilj je cijeli EN opseg.
I18N_CLEAN = [
    "src/Financije.jsx",
    "src/Vijesti.jsx",
    "src/Dividende.jsx",
    "src/Trziste.jsx",
    "src/Screener.jsx",
    "src/Usporedba.jsx",
    "src/Indeksi.jsx",
    "src/Obveznice.jsx",
    "src/MirovinskiFondovi.jsx",
    "src/i18n/LangContext.jsx",
]


@pytest.fixture(scope="module")
def dist():
    if not (DIST / "sitemap.xml").exists():
        pytest.skip("frontend nije buildan")
    return DIST


# ---------- hreflang reciprocitet (acceptance 2) ----------

def _page_alternates(html):
    out = {}
    for m in re.finditer(
            r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', html):
        out[m.group(1)] = m.group(2)
    return out


def _url_to_file(url):
    rel = url.replace(SITE, "").strip("/")
    return DIST / rel / "index.html" if rel else DIST / "index.html"


def test_hreflang_parovi_reciprocni(dist):
    """Svaka stranica s hreflang parovima: HR pokazuje na EN par i obrnuto,
    x-default postoji i vodi na HR; canonical je po jeziku (na sebe)."""
    checked = 0
    problems = []
    for f in dist.rglob("index.html"):
        html = f.read_text(encoding="utf-8")
        alts = _page_alternates(html)
        if not alts:
            continue
        checked += 1
        if set(alts) != {"hr", "en", "x-default"}:
            problems.append(f"{f}: hreflang skup {sorted(alts)}")
            continue
        if alts["x-default"] != alts["hr"]:
            problems.append(f"{f}: x-default nije HR")
        # recipročnost: par mora postojati i pokazivati natrag
        pair = _url_to_file(alts["en"]) if "/en" not in str(f) else _url_to_file(alts["hr"])
        if not pair.exists():
            problems.append(f"{f}: par {pair} ne postoji")
            continue
        pair_alts = _page_alternates(pair.read_text(encoding="utf-8"))
        if pair_alts.get("hr") != alts["hr"] or pair_alts.get("en") != alts["en"]:
            problems.append(f"{f}: par ne pokazuje natrag na iste URL-ove")
        # canonical po jeziku
        can = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        expect = alts["en"] if "/en/" in str(f) or str(f).endswith("/en/index.html") else alts["hr"]
        if can and can.group(1) != expect:
            problems.append(f"{f}: canonical {can.group(1)} != {expect}")
    assert checked >= 100, f"premalo stranica s hreflangom ({checked})"
    assert not problems, "hreflang problemi:\n" + "\n".join(problems[:15])


def test_en_rute_u_sitemapu(dist):
    sm = (dist / "sitemap.xml").read_text(encoding="utf-8")
    for u in (f"{SITE}/en", f"{SITE}/en/stock/koei", f"{SITE}/en/screener",
              f"{SITE}/en/dividends", f"{SITE}/en/methodology"):
        assert f"<loc>{u}</loc>" in sm, f"sitemap bez {u}"
    assert 'xhtml:link rel="alternate" hreflang="en"' in sm, \
        "sitemap bez hreflang alternates"


# ---------- centralno formatiranje (acceptance 3) ----------

def test_format_po_localeu():
    """Ista vrijednost: HR '1.035.725,00 €' vs EN '€1,035,725.00'; datumi
    lokalizirani. Test izvršava STVARNU format funkciju (node ESM)."""
    script = """
import { setLocale, num, eur, fmtDate } from '%s'
setLocale('hr')
console.log(JSON.stringify([num(1035725, 0), eur(1035725, 0), fmtDate('2026-07-16')]))
setLocale('en')
console.log(JSON.stringify([num(1035725, 0), eur(1035725, 0), fmtDate('2026-07-16')]))
""" % (FRONT / "src/format.js").as_posix()
    r = subprocess.run(["node", "--input-type=module", "-e", script],
                       capture_output=True, text=True, check=True)
    hr, en = [json.loads(line) for line in r.stdout.strip().split("\n")]
    assert hr[0] == "1.035.725" and en[0] == "1,035,725"
    assert hr[1] == "1.035.725 €" and en[1] == "€1,035,725"
    assert hr[2] == "16.7.2026." and en[2] == "16 Jul 2026"


def test_nema_rucnog_formatiranja_u_konvertiranim():
    """Konvertirane komponente ne smiju zvati toLocaleString direktno —
    sva prikazna formatiranja idu kroz format.js."""
    for rel in I18N_CLEAN:
        src = (FRONT / rel).read_text(encoding="utf-8")
        assert "toLocaleString" not in src.replace("format.js", ""), \
            f"{rel}: ručno formatiranje izvan format.js"


# ---------- lint hardkodiranih stringova (acceptance 4) ----------

CRO = re.compile(r"[čćžšđČĆŽŠĐ]")


def _hardcoded_croatian(src):
    """JSX tekstni čvorovi i string literali s hrvatskim dijakriticima.
    Heuristika: dijakritik bilo gdje izvan komentara = prekršaj (u čistoj
    komponenti smiju postojati samo t() ključevi, bez HR teksta)."""
    # makni komentare (/* */ i //) — dokumentacija smije biti hrvatska
    no_c = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    no_c = re.sub(r"//[^\n]*", "", no_c)
    return [ln.strip()[:80] for ln in no_c.split("\n") if CRO.search(ln)]


def test_lint_konvertirane_komponente_bez_hr_stringova():
    for rel in I18N_CLEAN:
        bad = _hardcoded_croatian((FRONT / rel).read_text(encoding="utf-8"))
        assert not bad, f"{rel}: hardkodirani HR stringovi:\n" + "\n".join(bad)


def test_lint_dokazano_pada_na_umjetnom_primjeru(tmp_path):
    """Acceptance 4: lint MORA uhvatiti hardkodirani string — umjetna
    komponenta s hrvatskim tekstom pada."""
    fake = 'export const X = () => <div>Fer-zona još nije izračunata</div>\n'
    assert _hardcoded_croatian(fake), \
        "lint NE hvata hardkodirani hrvatski string — brana ne radi"


def test_glosar_postoji_i_pokriva_kljucne_pojmove():
    g = (ROOT / "docs/glossary_hr_en.md").read_text(encoding="utf-8")
    for hr, en in [("fer-zona", "fair-value zone"), ("sidro", "anchor"),
                   ("održiva dividenda", "sustainable dividend"),
                   ("raskorak", "gap"), ("opravdani P/B", "justified P/B")]:
        assert hr in g and en in g, f"glosar bez para {hr} ↔ {en}"


def test_rjecnik_svaki_kljuc_ima_oba_jezika():
    src = (FRONT / "src/i18n/strings.mjs").read_text(encoding="utf-8")
    r = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ STR }} from '{(FRONT / 'src/i18n/strings.mjs').as_posix()}';"
         "const bad = Object.entries(STR).filter(([k,v]) => !v.hr || !v.en);"
         "console.log(JSON.stringify(bad.map(([k]) => k)))"],
        capture_output=True, text=True, check=True)
    bad = json.loads(r.stdout.strip())
    assert not bad, f"ključevi bez oba jezika: {bad}"
    assert "'common.na'" in src  # sanity da čitamo pravi file
