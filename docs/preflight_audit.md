# Pre-flight audit — 2026-07-13

Dijagnoza bez API poziva: baza + javni zse.hr scrape. Odluka o
ekstrakciji je urednička; ovo je popis nalaza, ne plan.

| Ticker | Status | Fer-zona € | Cijena vs zona | Nalazi |
|---|---|---|---|---|
| **ADPL** | FALI RAST · ODSTUPA OD TRŽIŠTA | 49.00–66.30 (30%) | -47% | cijena -47% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda +103% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ADRS** | ODSTUPA OD TRŽIŠTA | 64.34–72.92 (12%) | +140% | cijena +140% vs sredina fer-zone (prag ±40%) |
| **ARNT** | FALI RAST · ODSTUPA OD TRŽIŠTA | 56.79–150.63 (90%) | -60% | cijena -60% vs sredina fer-zone (prag ±40%)<br>raspon sidra 90% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: multiples_relative -46% vs primarno sidro<br>nekonzistentno sidro: ev_ebitda -77% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ATGR** | FALI RAST · ODSTUPA OD TRŽIŠTA | 27.45–37.13 (30%) | +56% | cijena +56% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **BSQR** | NEEDS EXTRACTION (discovered) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **CROS** | ODSTUPA OD TRŽIŠTA | 1,577.65–2,288.90 (37%) | +72% | cijena +72% vs sredina fer-zone (prag ±40%)<br>raspon sidra 37% > 20% (osjetljivost na r — nije min-max)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi |
| **CTKS** | NEEDS EXTRACTION (needs_review) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **DLKV** | ODSTUPA OD TRŽIŠTA · FALI RAST | 4.48–5.52 (21%) | +256% | cijena +256% vs sredina fer-zone (prag ±40%)<br>raspon sidra 21% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **HPB** | NEEDS EXTRACTION (needs_review) · FALI RAST | 326.65–465.35 (35%) | -16% | raspon sidra 35% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: residual_income -26% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 0: ništa) -> rast se ne izvodi |
| **HT** | NEEDS EXTRACTION (needs_review) · FALI RAST | 27.18–36.78 (30%) | +28% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: neto dobit |
| **IG** | FALI RAST | 55.87–75.58 (30%) | +9% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2024) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina |
| **KODT** | FALI RAST | 3,355.05–4,110.20 (20%) | +22% | raspon sidra 20% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: multiples_relative +26% vs primarno sidro<br>nekonzistentno sidro: ev_ebitda +134% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **KOEI** | ODSTUPA OD TRŽIŠTA · FALI RAST | 611.85–693.44 (13%) | +53% | cijena +53% vs sredina fer-zone (prag ±40%)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **KTJV** | NEEDS EXTRACTION (needs_review) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **MAIS** | NEEDS EXTRACTION (discovered) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **PLAG** | NEEDS EXTRACTION (discovered) · FALI RAST | 411.05–556.12 (30%) | -30% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda -49% vs primarno sidro<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **PODR** | ODSTUPA OD TRŽIŠTA · FALI RAST | 23.25–81.77 (111%) | +208% | cijena +208% vs sredina fer-zone (prag ±40%)<br>raspon sidra 111% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: multiples_relative +442% vs primarno sidro<br>nekonzistentno sidro: ev_ebitda +223% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **RIVP** | FALI RAST · ODSTUPA OD TRŽIŠTA | 3.95–5.34 (30%) | +80% | cijena +80% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **SPAN** | FALI RAST · ODSTUPA OD TRŽIŠTA | 29.97–40.54 (30%) | +62% | cijena +62% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **TOK** | FALI RAST | 12.93–17.49 (30%) | +12% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda +53% vs primarno sidro<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **UCG** | NEEDS EXTRACTION (discovered) · FALI BROJ DIONICA · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>broj dionica (ni share_classes ni shares_outstanding)<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **ULPL** | NEEDS EXTRACTION (needs_review) · FALI RAST | 137.60–222.51 (47%) | n/p | raspon sidra 47% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: multiples_relative -79% vs primarno sidro<br>nekonzistentno sidro: ev_ebitda -51% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2024) -> rast se ne izvodi |
| **VLEN** | NEEDS EXTRACTION (needs_review) · FALI RAST | 2.23–3.02 (30%) | n/p | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda +136% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ZABA** | NEKONZISTENTNO | 19.14–25.42 (28%) | +1% | raspon sidra 28% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: residual_income -52% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi |
| **ZITO** | FALI RAST | 17.39–23.53 (30%) | -11% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |

## Sistemska pristranost
- firmi s valuacijom: 18; iznad zone: 13, ispod: 5
- ALARM: 72% firmi trguje IZNAD fer-zone (model sustavno PODcjenjuje) — prag 70%
