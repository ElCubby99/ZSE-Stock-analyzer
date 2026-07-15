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
