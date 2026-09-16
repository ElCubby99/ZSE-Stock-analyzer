"""M80: izdanja newslettera (data/newsletter/*) moraju proći iste brane kao
AI sadržaj — bez preporuka (MAR) i s obveznim linkom za odjavu u OBA tijela.

Ne traži bazu ni mrežu: validira datoteke u repou prije nego ijedan mail
napusti sustav.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.send_newsletter import load  # noqa: E402
from src.summons import forbidden_hit  # noqa: E402

SRC = ROOT / "data" / "newsletter"
SLUGS = sorted(p.stem for p in SRC.glob("*.json")) if SRC.exists() else []


def test_postoji_bar_jedno_izdanje():
    assert SLUGS, "nema izdanja u data/newsletter/"


@pytest.mark.parametrize("slug", SLUGS)
def test_izdanje_prolazi_validaciju(slug):
    """load() nosi sve brane: subject, oba tijela, MAR filter, {{UNSUBSCRIBE_URL}}."""
    import os
    os.chdir(ROOT)
    payload = load(slug)
    assert payload["lang"] in ("hr", "en")
    assert payload["subject"].strip()


@pytest.mark.parametrize("slug", SLUGS)
def test_odjava_i_mar_u_oba_tijela(slug):
    html = (SRC / f"{slug}.html").read_text(encoding="utf-8")
    text = (SRC / f"{slug}.txt").read_text(encoding="utf-8")
    for label, body in (("html", html), ("txt", text)):
        assert "{{UNSUBSCRIBE_URL}}" in body, \
            f"{slug}/{label}: nedostaje link za odjavu (zakonska obveza)"
        hit = forbidden_hit(body)
        assert not hit, f"{slug}/{label}: MAR filter ({hit})"


@pytest.mark.parametrize("slug", SLUGS)
def test_disclaimer_u_izdanju(slug):
    """Svako izdanje nosi napomenu da nije investicijski savjet."""
    text = (SRC / f"{slug}.txt").read_text(encoding="utf-8").lower()
    assert "investicijski savjet" in text or "investment advice" in text, \
        f"{slug}: izdanje bez napomene o informativnom sadržaju"
