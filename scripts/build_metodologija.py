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

SRC = ROOT / "docs" / "metodologija.md"
OUT = ROOT / "frontend" / "public" / "data" / "metodologija.json"


def main() -> int:
    md = SRC.read_text(encoding="utf-8")
    lines = md.split("\n")
    title = lines[0].lstrip("# ").strip()
    body = "\n".join(lines[1:])
    OUT.write_text(json.dumps({
        "title": title,
        "version": "v2.3",
        "updated": "2026-07-16",
        "html": md_to_html(body),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[metodologija] zapisano {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
