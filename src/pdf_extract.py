"""PDF -> tekst (PyMuPDF). Za pripremu izvora prije ekstrakcije.

CLI:
  python -m src.pdf_extract data/reports/koei_2024.pdf data/reports/koei_2024.txt
  python -m src.pdf_extract in.pdf out.txt --pages 23-33,134-136   # slice (1-based, uklj.)
Bez drugog argumenta ispisuje na stdout.
"""
from __future__ import annotations

import sys


def parse_pages(spec: str) -> list[int]:
    """'23-33,134-136' -> [23..33, 134..136] (1-based, uključivo)."""
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a), int(b) + 1))
        elif part:
            pages.append(int(part))
    return pages


def pdf_to_text(pdf_path: str, pages: list[int] | None = None) -> str:
    import fitz  # PyMuPDF

    parts = []
    with fitz.open(pdf_path) as doc:
        wanted = set(pages) if pages else None
        for i, page in enumerate(doc, start=1):
            if wanted is not None and i not in wanted:
                continue
            parts.append(f"\n===== STRANICA {i} =====\n")
            parts.append(page.get_text("text"))
    return "".join(parts)


def main(argv=None) -> int:
    argv = list(argv or sys.argv[1:])
    pages = None
    if "--pages" in argv:
        i = argv.index("--pages")
        pages = parse_pages(argv[i + 1])
        del argv[i:i + 2]
    if not argv:
        print("usage: python -m src.pdf_extract <in.pdf> [out.txt] [--pages 23-33,134-136]",
              file=sys.stderr)
        return 2
    text = pdf_to_text(argv[0], pages)
    if len(argv) > 1:
        with open(argv[1], "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Zapisano {len(text)} znakova u {argv[1]}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
