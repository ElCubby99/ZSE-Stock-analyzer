#!/usr/bin/env python3
"""M80: slanje izdanja newslettera kroz Edge Function `newsletter`.

Sadržaj izdanja živi u repou (verzioniran, pregledan prije slanja):
    data/newsletter/<slug>.json   meta: slug, lang, subject
    data/newsletter/<slug>.html   HTML tijelo
    data/newsletter/<slug>.txt    plain-text tijelo (obavezno)

Oba tijela smiju sadržavati {{UNSUBSCRIBE_URL}} — Edge Function ga
zamjenjuje osobnim tokenom SVAKOG primatelja (RFC 8058 jednoklik odjava).

Slanje ide ISKLJUČIVO potvrđenim pretplatnicima (status='confirmed') tog
jezika; nepotvrđeni i odjavljeni se ne diraju. Test:

    python -m scripts.send_newsletter <slug> --test-to boris@primjer.hr

šalje samo na tu adresu (mora već biti potvrđeni pretplatnik). Bez
--test-to skripta TRAŽI --confirm-all kao branu od slučajnog masovnog
slanja.

Env: SUPABASE_URL + BLOG_API_KEY (isti ključ kao blog-publish).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")

from src.summons import forbidden_hit  # noqa: E402  (jedan izvor MAR pravila)

SRC = pathlib.Path("data/newsletter")


def load(slug: str) -> dict:
    meta = json.loads((SRC / f"{slug}.json").read_text(encoding="utf-8"))
    html = (SRC / f"{slug}.html").read_text(encoding="utf-8")
    text = (SRC / f"{slug}.txt").read_text(encoding="utf-8")
    assert meta.get("subject"), f"{slug}: subject je obavezan"
    assert text.strip(), f"{slug}: plain-text tijelo je obavezno"
    # MAR brana: izdanje ne smije sadržavati preporuku. Koristi se ISTI
    # filter kao za AI postove (src/summons.FORBIDDEN_RX) — granice riječi
    # znače da "skupinu" i "prodaju dionica" ne pale lažni alarm, a
    # "kupite"/"prodajte"/"ciljna cijena" pale.
    for label, body in (("subject", meta["subject"]), ("text", text), ("html", html)):
        hit = forbidden_hit(body)
        assert not hit, f"{slug}: MAR filter u {label} ({hit})"
    assert "{{UNSUBSCRIBE_URL}}" in text, f"{slug}: text bez {{{{UNSUBSCRIBE_URL}}}}"
    assert "{{UNSUBSCRIBE_URL}}" in html, f"{slug}: html bez {{{{UNSUBSCRIBE_URL}}}}"
    return {"subject": meta["subject"], "lang": meta.get("lang", "hr"),
            "html": html, "text": text}


def send(payload: dict, test_to: str | None) -> int:
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("BLOG_API_KEY", "")
    if not base or not key:
        print("[newsletter] SUPABASE_URL ili BLOG_API_KEY nisu postavljeni — stop")
        return 1
    body = {"action": "send_issue", **payload}
    if test_to:
        body["test_to"] = test_to
    req = urllib.request.Request(
        f"{base}/functions/v1/newsletter",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            out = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        print(f"[newsletter] HTTP {e.code}: {detail}")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[newsletter] poziv pao: {type(e).__name__}: {e}")
        return 1
    print(f"[newsletter] odgovor: {json.dumps(out, ensure_ascii=False)}")
    if not out.get("ok"):
        return 1
    if out.get("failed"):
        print(f"[newsletter] UPOZORENJE: {out['failed']} adresa nije primilo mail")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="npr. 2026-09-ai-forum-zaba")
    ap.add_argument("--test-to", default=None,
                    help="šalji SAMO na ovu adresu (potvrđeni pretplatnik)")
    ap.add_argument("--confirm-all", action="store_true",
                    help="obavezno za masovno slanje svim potvrđenima")
    ap.add_argument("--dry-run", action="store_true",
                    help="samo provjeri sadržaj, bez slanja")
    a = ap.parse_args(argv)

    payload = load(a.slug)
    print(f"[newsletter] {a.slug}: subject={payload['subject']!r} "
          f"lang={payload['lang']} html={len(payload['html'])}b "
          f"text={len(payload['text'])}b — validacija OK")
    if a.dry_run:
        return 0
    if not a.test_to and not a.confirm_all:
        print("[newsletter] masovno slanje traži --confirm-all (brana); "
              "za test koristi --test-to")
        return 2
    return send(payload, a.test_to)


if __name__ == "__main__":
    sys.exit(main())
