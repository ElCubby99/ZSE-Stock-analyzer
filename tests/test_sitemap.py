"""Brana za sitemap regresiju: rute smiju postojati SAMO kroz
frontend/src/routes/registry.mjs. Provjerava (1) da router i prerender
nemaju vlastite, paralelne liste ruta i (2) da se build output (dist/)
i sitemap.xml 1:1 poklapaju — svaka indeksabilna generirana stranica je
u sitemapu i svaki sitemap URL odgovara stvarno generiranoj stranici.
Test pada ako se nova stranica doda mimo registryja ili sitemap sadrži
mrtav URL."""
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest

FRONT = pathlib.Path("frontend")
DIST = FRONT / "dist"
SITE = "https://burzovnilist.com"


def test_router_i_prerender_citaju_samo_registry():
    """Statička provjera bez builda: nijedan hardkodirani path u routeru,
    prerender uvozi registry (nema vlastitu listu ruta)."""
    main = (FRONT / "src/main.jsx").read_text(encoding="utf-8")
    assert "routes/registry.mjs" in main, \
        "main.jsx mora graditi rute iz src/routes/registry.mjs"
    hardcoded = re.findall(r"path:\s*['\"](/[^'\"]*)['\"]", main)
    assert not hardcoded, \
        f"hardkodirane rute u main.jsx (idu u registry): {hardcoded}"

    pre = (FRONT / "scripts/prerender.mjs").read_text(encoding="utf-8")
    assert "routes/registry.mjs" in pre, \
        "prerender.mjs mora čitati rute iz src/routes/registry.mjs"
    assert "staticPages" not in pre, \
        "prerender.mjs ne smije imati vlastitu listu statičkih ruta"


@pytest.fixture(scope="module")
def dist():
    if not (DIST / "sitemap.xml").exists():
        pytest.skip("frontend nije buildan (cd frontend && npm run build) — "
                    "dist/sitemap.xml ne postoji; milestone workflow builda "
                    "prije testova pa je na CI-ju ovo uvijek aktivno")
    return DIST


def _generated_routes(dist_dir):
    """Sve stvarno generirane HTML stranice u dist/ → (url, indexable)."""
    out = {}
    for f in dist_dir.rglob("index.html"):
        rel = f.parent.relative_to(dist_dir).as_posix()
        url = f"{SITE}/" if rel == "." else f"{SITE}/{rel}"
        html = f.read_text(encoding="utf-8")
        noindex = re.search(
            r'<meta name="robots" content="[^"]*noindex', html)
        out[url] = noindex is None
    return out


def _sitemap_urls(dist_dir):
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(dist_dir / "sitemap.xml").getroot()
    return {u.findtext("sm:loc", namespaces=ns) for u in root.findall("sm:url", ns)}


def test_svaka_indeksabilna_stranica_je_u_sitemapu(dist):
    generated = _generated_routes(dist)
    sitemap = _sitemap_urls(dist)
    indexable = {u for u, ok in generated.items() if ok}
    missing = indexable - sitemap
    assert not missing, (
        "generirane indeksabilne stranice NEDOSTAJU u sitemapu (ruta dodana "
        f"mimo registryja?): {sorted(missing)}")


def test_sitemap_nema_mrtvih_ni_noindex_urlova(dist):
    generated = _generated_routes(dist)
    sitemap = _sitemap_urls(dist)
    dead = sitemap - set(generated)
    assert not dead, f"sitemap sadrži URL-ove bez generirane stranice: {sorted(dead)}"
    noindexed = {u for u in sitemap if generated.get(u) is False}
    assert not noindexed, f"noindex stranice ne smiju u sitemap: {sorted(noindexed)}"


# ---------- M33: content markeri — prazna SPA ljuska = pad ----------
# Brana koja je nedostajala kad je Z5 acceptance "prošao" na meta tagovima,
# a ruta godinama bila prazna za crawlere.

FOOTER_LINKS = ["/impressum", "/politika-privatnosti", "/uvjeti-koristenja",
                "/politika-kolacica"]
TABLE_ROUTES = {  # ruta -> minimalan broj redaka podataka
    f"{SITE}/screener": 60,
    f"{SITE}/usporedba": 60,
    f"{SITE}/dividende": 10,
    f"{SITE}/obveznice": 25,
}
MIN_TEXT = {  # ruta -> minimalan broj znakova VIDLJIVOG teksta u #root
    f"{SITE}/": 2000,
    f"{SITE}/screener": 2000,
    f"{SITE}/usporedba": 2000,
    f"{SITE}/dividende": 2000,
    f"{SITE}/obveznice": 2000,
    f"{SITE}/mirovinski-fondovi": 1200,
    f"{SITE}/indeksi": 1500,
    f"{SITE}/metodologija": 1500,
    f"{SITE}/impressum": 1500,
    f"{SITE}/uvjeti-koristenja": 2000,
    f"{SITE}/politika-privatnosti": 2000,
    f"{SITE}/politika-kolacica": 2000,
}
DEFAULT_MIN_TEXT = 400  # dionice, blog i ostalo: nikad prazna ljuska


def _root_text(html):
    """Vidljivi tekst unutar <div id="root">…</div> (bez tagova)."""
    start = html.find('<div id="root">')
    end = html.find("</body>", start)
    inner = html[start:end] if start != -1 else ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner)).strip()


def _dist_file(dist_dir, url):
    rel = url.replace(SITE, "").strip("/")
    return dist_dir / rel / "index.html" if rel else dist_dir / "index.html"


def test_content_markeri_nijedna_ruta_nije_prazna_ljuska(dist):
    problems = []
    for url in sorted(_sitemap_urls(dist)):
        html = _dist_file(dist, url).read_text(encoding="utf-8")
        text = _root_text(html)
        need = MIN_TEXT.get(url, DEFAULT_MIN_TEXT)
        if len(text) < need:
            problems.append(f"{url}: samo {len(text)} znakova teksta (< {need})")
        if "<h1>" not in html:
            problems.append(f"{url}: nema <h1>")
        for link in FOOTER_LINKS:
            if f'href="{link}"' not in html:
                problems.append(f"{url}: footer bez {link}")
        rows_min = TABLE_ROUTES.get(url)
        if rows_min and html.count("<tr>") < rows_min:
            problems.append(f"{url}: {html.count('<tr>')} redaka (< {rows_min})")
    assert not problems, "prazne ljuske / rupe u statičkom HTML-u:\n" + "\n".join(problems)


def test_screener_sadrzi_puna_imena_firmi(dist):
    """Acceptance 1+2: uz ticker mora stajati PUNO ime firme."""
    scr = (dist / "screener/index.html").read_text(encoding="utf-8")
    home = (dist / "index.html").read_text(encoding="utf-8")
    for frag in ("Podravka d.d.", "Zagrebačka banka d.d."):
        assert frag in scr, f"screener bez imena: {frag}"
        assert frag in home, f"naslovnica bez imena: {frag}"
