#!/usr/bin/env python3
"""M17: docs/metodologija.md -> frontend/public/data/metodologija.json.

Ista md->html mehanika kao blog (scripts/build_blog.py) — jedan izvor istine:
stranica /metodologija renderira ovaj JSON, tekst se uređuje SAMO u docs/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_blog import md_to_html  # noqa: E402

# M38: dva jezika, isti mehanizam — EN je PUNI prijevod (trust dokument),
# uređuje se SAMO u docs/ (docs/metodologija_en.md)
DOCS = [
    (ROOT / "docs" / "metodologija.md",
     ROOT / "frontend" / "public" / "data" / "metodologija.json"),
    (ROOT / "docs" / "metodologija_en.md",
     ROOT / "frontend" / "public" / "data" / "metodologija_en.json"),
]


def main() -> int:
    for src, out in DOCS:
        md = src.read_text(encoding="utf-8")
        lines = md.split("\n")
        title = lines[0].lstrip("# ").strip()
        body = "\n".join(lines[1:])
        out.write_text(json.dumps({
            "title": title,
            "version": "v2.5",
            "updated": "2026-07-24",
            "html": md_to_html(body),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[metodologija] zapisano {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
