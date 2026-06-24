"""PDF -> tekst (PyMuPDF). Za pripremu izvora prije ekstrakcije.

CLI:
  python -m src.pdf_extract data/reports/koei_2024.pdf data/reports/koei_2024.txt
Bez drugog argumenta ispisuje na stdout.
"""
from __future__ import annotations

import sys


def pdf_to_text(pdf_path: str) -> str:
    import fitz  # PyMuPDF

    parts = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            parts.append(f"\n===== STRANICA {i} =====\n")
            parts.append(page.get_text("text"))
    return "".join(parts)


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: python -m src.pdf_extract <in.pdf> [out.txt]", file=sys.stderr)
        return 2
    text = pdf_to_text(argv[0])
    if len(argv) > 1:
        with open(argv[1], "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Zapisano {len(text)} znakova u {argv[1]}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
