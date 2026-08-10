"""M64: parser mjesečnog izvještaja (factsheeta) InterCapital UCITS ETF-ova.

Izdavatelj objavljuje mjesečni izvještaj po pod-fondu na EHO-u u jednakom
predlošku: opći podaci (NAV, cijena udjela, benchmark…), naknade (TER),
izabrani pokazatelji (dionički: P/E, div. prinos, ROE; obveznički/novčani:
prosj. dospijeće, mod. duracija, prosj. prinos do dospijeća), deset
najvećih pozicija s udjelima i tablica prinosa po razdobljima.

Ekstrakcija je POZICIJSKA (riječi s koordinatama), jer redoslijed čistog
teksta zna ispremiješati stupce. STROGI GATEOVI (CLAUDE.md: radije prazno
s razlogom nego kriva brojka):
  - pokazatelji obvezničkih fondova: mod. duracija <= prosj. dospijeće,
    inače se pokazatelji ODBACUJU s razlogom;
  - udjeli pozicija: zbroj 80-105% (top-10 + ostalo), inače se pozicije
    odbacuju;
  - naknade: TER > 0 i TER < 5%, komponente <= TER + tolerancija.
Sve što ne prođe gate vraća se u out["skipped"] s razlogom.
"""
from __future__ import annotations

import re

NUM = re.compile(r"^-?\d{1,3}(?:\.\d{3})*(?:,\d+)?%?$")
HOLDING_TYPES = ("Dionica", "Obveznica", "Trezorski", "Depozit", "Račun",
                 "Novac", "Ostalo", "GDR", "Udjel")
PERIOD_LABELS = ("Godišnji prosjek od osnutka", "1 mjesec (1M)",
                 "Tekuća godina (YTD)", "1 godina (1Y)")


def _f(s: str):
    s = s.replace("%", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _lines(page):
    """Riječi grupirane u vizualne retke (po y sredini, tolerancija 3pt)."""
    words = page.get_text("words")  # (x0, y0, x1, y1, text, ...)
    rows: dict[int, list] = {}
    for w in words:
        yc = round((w[1] + w[3]) / 2 / 3)
        rows.setdefault(yc, []).append(w)
    out = []
    for yc in sorted(rows):
        ws = sorted(rows[yc], key=lambda w: w[0])
        out.append({"y": yc * 3, "words": ws,
                    "text": " ".join(w[4] for w in ws)})
    return out


def _fees(lines, out, skipped):
    fees = {}
    LBL = {"Naknada za upravljanje": "management",
           "Naknada depozitaru": "depositary",
           "Ostali troškovi": "other",
           "Ukupni troškovi (TER)": "ter",
           "Transakcijski troškovi": "transaction"}
    for ln in lines:
        for lab, key in LBL.items():
            if lab in ln["text"]:
                m = re.search(r"(\d+,\d+)\s*%", ln["text"])
                if m:
                    fees[key] = _f(m.group(1))
    ter = fees.get("ter")
    if ter is None or not (0 < ter < 5):
        skipped.append(f"naknade: TER izvan gatea ({ter})")
        return
    comp = [fees.get(k) for k in ("management", "depositary", "other")]
    if all(c is not None for c in comp) and sum(comp) > ter + 0.06:
        skipped.append(f"naknade: komponente {sum(comp):.2f} > TER {ter:.2f}")
        return
    out["fees_pct"] = fees


def _equity_indicators(lines, out):
    for ln in lines:
        m = re.match(r"^(-?\d+,\d+)\s+Odnos cijene i zarade \(P/E\)", ln["text"])
        if m:
            out.setdefault("portfolio_indicators", {})["pe"] = _f(m.group(1))
        m = re.match(r"^(-?\d+,\d+)\s+Dividendni prinos, %", ln["text"])
        if m:
            out.setdefault("portfolio_indicators", {})["div_yield_pct"] = _f(m.group(1))
        m = re.match(r"^(-?\d+,\d+)\s+Povrat na kapital \(ROE\), %", ln["text"])
        if m:
            out.setdefault("portfolio_indicators", {})["roe_pct"] = _f(m.group(1))
    if out.get("portfolio_indicators"):
        out["portfolio_indicators"]["kind"] = "equity"


def _value_below(lines, label_ln, label_kw, y_max=32, pattern=None):
    """Prva vrijednost ISPOD labela, poravnata s njegovim lijevim rubom
    (factsheet slaže label-red pa vrijednost-red u istoj koloni)."""
    kw_words = [w for w in label_ln["words"] if label_kw.split()[0] in w[4]]
    x0 = min(w[0] for w in kw_words) if kw_words else min(w[0] for w in label_ln["words"])
    best = None
    for cand in lines:
        if not (label_ln["y"] < cand["y"] <= label_ln["y"] + y_max):
            continue
        for w in cand["words"]:
            if pattern and not pattern.match(w[4]):
                continue
            if x0 - 40 <= w[0] <= x0 + 60:
                d = cand["y"] - label_ln["y"]
                if best is None or d < best[0]:
                    best = (d, w[4])
    return best[1] if best else None


def _bond_indicators(page, lines, out, skipped):
    """Tri okvira: label (+podnaslov s jedinicom), vrijednost u retku ispod —
    uparivanje po lijevom rubu kolone; gate: duracija <= dospijeće."""
    labels = {}
    unit = None
    KW = {"maturity": "Prosječno dospijeće", "duration": "Modificirana duracija",
          "ytm": "prinos do dospijeća"}
    for ln in lines:
        for key, kw in KW.items():
            if kw.lower() in ln["text"].lower() and key not in labels:
                labels[key] = ln
        if "u godinama" in ln["text"]:
            unit = "godine"
        elif "u mjesecima" in ln["text"]:
            unit = "mjeseci"
    if len(labels) < 3:
        return
    numpat = re.compile(r"^-?\d+,\d+$")
    vals = {}
    for key, ln in labels.items():
        # vrijednost zna biti ispod dvorednog podnaslova -> šire y okno
        v = _value_below(lines, ln, KW[key], y_max=48, pattern=numpat)
        if v is not None:
            vals[key] = _f(v)
    if len(vals) < 3:
        skipped.append(f"obveznički pokazatelji: nepotpuno uparivanje ({vals})")
        return
    if vals["duration"] > vals["maturity"] + 0.01:
        skipped.append(
            f"obveznički pokazatelji: duracija {vals['duration']} > "
            f"dospijeće {vals['maturity']} — odbačeno (kriva ekstrakcija?)")
        return
    out["portfolio_indicators"] = {
        "kind": "fixed_income", "unit": unit or "godine",
        "avg_maturity": vals["maturity"], "mod_duration": vals["duration"],
        "avg_ytm_pct": vals["ytm"],
    }


HOLDING_ROW = re.compile(
    r"(Dionica|Obveznica|Trezorski zapis|Depozit|Račun|Novac i ostalo|"
    r"Ostalo|GDR|Udjel)\s*(.*?)\s*(-?\d{1,2},\d)\s*%$")


def _holdings(page1_lines, out, skipped):
    """Redci 'Vrsta Oznaka Izdavatelj Udio' tablice — redci znaju biti
    ispremiješani s tekstom opisa (dvokolonski layout) pa se hvataju
    regexom bilo gdje u retku, SAMO na 1. stranici (2. stranica ima
    alokacijske grafove sa sličnim parovima)."""
    rows = []
    for ln in page1_lines:
        m = HOLDING_ROW.search(ln["text"])
        if not m:
            continue
        typ, body, w = m.group(1), m.group(2).strip(), _f(m.group(3))
        ticker = body.split()[0] if typ == "Dionica" and body else None
        rows.append({"type": typ, "name": (f"{typ} {body}".strip() if body else typ),
                     "ticker": ticker, "weight_pct": w})
    if not rows:
        skipped.append("pozicije: tablica nije pronađena")
        return
    tot = sum(r["weight_pct"] for r in rows)
    if not (80 <= tot <= 105):
        skipped.append(f"pozicije: zbroj udjela {tot:.1f}% izvan 80-105% — odbačeno")
        return
    out["holdings"] = rows


def _performance(lines, out):
    perf = []
    for ln in lines:
        t = ln["text"]
        lab = next((p for p in PERIOD_LABELS if t.startswith(p)), None)
        if lab is None:
            m = re.match(r"^(20\d\d)\s+(-?\d+,\d+)\s*%(?:\s+(-?\d+,\d+)\s*%)?$", t)
            if m:
                perf.append({"period": m.group(1), "fund_pct": _f(m.group(2)),
                             "benchmark_pct": _f(m.group(3)) if m.group(3) else None})
            continue
        nums = re.findall(r"(-?\d+,\d+)\s*%", t)
        if nums:
            perf.append({"period": lab, "fund_pct": _f(nums[0]),
                         "benchmark_pct": _f(nums[1]) if len(nums) > 1 else None})
    if perf:
        out["performance"] = perf


def _facts(lines, out):
    """Opći podaci: label-red pa vrijednost-red u istoj koloni (kao
    obveznički pokazatelji) — vrijednost ispod lijevog ruba labela."""
    txt = "\n".join(ln["text"] for ln in lines)
    m = re.search(r"Mjesečni izvještaj za\s+(.+?)\s*(20\d\d)", txt)
    if m:
        out["report_period"] = f"{m.group(1)} {m.group(2)}."
    FACTS = {
        "nav_meur": ("NAV:", re.compile(r"^\d+(,\d+)?$")),
        "unit_value": ("Cijena udjela:", re.compile(r"^\d{1,4},\d{2,4}$")),
        "inception_date": ("Datum početka klase:", re.compile(r"^\d{1,2}\.\d{1,2}\.20\d\d\.?$")),
        "fund_type": ("Vrsta fonda:", re.compile(r"^[A-ZČĆŽŠĐ][a-zčćžšđ]+$")),
    }
    for key, (label, pat) in FACTS.items():
        for ln in lines:
            if label in ln["text"]:
                v = _value_below(lines, ln, label, pattern=pat)
                if v is not None:
                    if key == "inception_date":
                        d, mo, y = v.rstrip(".").split(".")[:3]
                        out[key] = f"{y}-{int(mo):02d}-{int(d):02d}"
                    elif key == "fund_type":
                        out[key] = v
                    else:
                        out[key] = _f(v)
                    break


def parse_factsheet(pdf_bytes: bytes) -> dict:
    """-> dict s poljima koja su PROŠLA gateove + out['skipped'] razlozi."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out: dict = {"skipped": []}
    skipped = out["skipped"]
    page1_lines = _lines(doc[0])
    all_lines = list(page1_lines)
    for page in list(doc)[1:]:
        all_lines.extend(_lines(page))
    _fees(all_lines, out, skipped)
    _equity_indicators(all_lines, out)
    if "portfolio_indicators" not in out:
        _bond_indicators(doc[0], page1_lines, out, skipped)
    _holdings(page1_lines, out, skipped)
    _performance(all_lines, out)
    _facts(page1_lines, out)
    return out
