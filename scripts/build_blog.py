#!/usr/bin/env python3
"""Statični blog build: content/blog/*.md (frontmatter) -> frontend/public/blog/
(index.json + <slug>.json s pre-renderiranim HTML-om). Bez backend poziva —
frontend čita statične JSON-ove. Pokreće se ručno ili iz daily-ja (nightly).
Markdown podskup: ## naslovi, odlomci, - liste (i uvučeni nastavci stavke),
1. numerirane liste, **bold**, *italic*, [tekst](url) linkovi."""
import html
import json
import os
import re
import sys

SRC = "content/blog"
OUT = "frontend/public/blog"


def md_to_html(md: str) -> str:
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
        return s
    out, para, ul, ol = [], [], [], []

    def flush():
        if ul:
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in ul) + "</ul>")
            ul.clear()
        if ol:
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in ol) + "</ol>")
            ol.clear()
        if para:
            out.append("<p>" + " ".join(para) + "</p>")
            para.clear()
    for line in md.splitlines():
        s = line.strip()
        m_ol = re.match(r"^(\d+)[.)]\s+(.*)", s)
        if s.startswith("## "):
            flush(); out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("- "):
            if para or ol: flush()
            ul.append(inline(s[2:]))
        elif m_ol:
            if para or ul: flush()
            ol.append(inline(m_ol.group(2)))
        elif not s:
            flush()
        elif (ul or ol) and line.startswith(("  ", "\t")):
            # uvučeni nastavak višeretčane stavke liste — lijepi se na zadnju
            tgt = ul if ul else ol
            tgt[-1] += " " + inline(s)
        else:
            if ul or ol: flush()
            para.append(inline(s))
    flush()
    return "\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        slug = fn[:-3]
        raw = open(os.path.join(SRC, fn), encoding="utf-8").read()
        m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        if not m:
            print(f"[skip] {fn}: nema frontmattera"); continue
        meta = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
        post = {"slug": slug, "title": meta.get("title", slug),
                "category": meta.get("category", "Edukacija"),
                "date": meta.get("date"), "summary": meta.get("summary", ""),
                "html": md_to_html(m.group(2))}
        with open(f"{OUT}/{slug}.json", "w", encoding="utf-8") as f:
            json.dump(post, f, ensure_ascii=False)
        index.append({k: post[k] for k in ("slug", "title", "category", "date", "summary")})
    index.sort(key=lambda p: p["date"] or "", reverse=True)
    with open(f"{OUT}/index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    print(f"blog: {len(index)} postova -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
