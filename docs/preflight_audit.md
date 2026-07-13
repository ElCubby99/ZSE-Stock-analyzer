# Pre-flight audit — 2026-07-13

Dijagnoza bez API poziva: baza + javni zse.hr scrape. Odluka o
ekstrakciji je urednička; ovo je popis nalaza, ne plan.

| Ticker | Status | Fer-zona € | Cijena vs zona | Nalazi |
|---|---|---|---|---|
| **ADPL** | FALI RAST · ODSTUPA OD TRŽIŠTA | 55.37–74.91 (30%) | -54% | cijena -54% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda +79% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ADRS** | ODSTUPA OD TRŽIŠTA | 64.34–72.92 (12%) | +140% | cijena +140% vs sredina fer-zone (prag ±40%) |
| **ARNT** | FALI RAST · ODSTUPA OD TRŽIŠTA | 56.79–150.63 (90%) | -60% | cijena -60% vs sredina fer-zone (prag ±40%)<br>raspon sidra 90% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: multiples_relative -46% vs primarno sidro<br>nekonzistentno sidro: ev_ebitda -77% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ATGR** | FALI RAST · ODSTUPA OD TRŽIŠTA | 27.75–37.54 (30%) | +55% | cijena +55% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **BSQR** | NEEDS EXTRACTION (discovered) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **CROS** | ODSTUPA OD TRŽIŠTA | 1,577.65–2,288.90 (37%) | +72% | cijena +72% vs sredina fer-zone (prag ±40%)<br>raspon sidra 37% > 20% (osjetljivost na r — nije min-max)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi |
| **CTKS** | NEEDS EXTRACTION (needs_review) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **DLKV** | FALI RAST · ODSTUPA OD TRŽIŠTA | 4.13–5.08 (21%) | +287% | cijena +287% vs sredina fer-zone (prag ±40%)<br>raspon sidra 21% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **HPB** | NEEDS EXTRACTION (needs_review) · FALI RAST | 326.65–465.35 (35%) | -16% | raspon sidra 35% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: residual_income -26% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 0: ništa) -> rast se ne izvodi |
| **HT** | NEEDS EXTRACTION (needs_review) · FALI RAST | 27.18–36.78 (30%) | +28% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: neto dobit |
| **IG** | FALI RAST | 71.28–96.43 (30%) | -15% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2024) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina |
| **KODT** | FALI RAST | 3,001.46–3,665.59 (20%) | +36% | nekonzistentno sidro: multiples_relative +231% vs primarno sidro<br>nekonzistentno sidro: ev_ebitda +162% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **KOEI** | FALI RAST · ODSTUPA OD TRŽIŠTA | 576.89–653.80 (13%) | +62% | cijena +62% vs sredina fer-zone (prag ±40%)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **KTJV** | NEEDS EXTRACTION (needs_review) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **MAIS** | NEEDS EXTRACTION (discovered) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **PLAG** | NEEDS EXTRACTION (discovered) · FALI RAST | 429.25–580.75 (30%) | -33% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda -51% vs primarno sidro<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **PODR** | FALI RAST · ODSTUPA OD TRŽIŠTA | 17.44–70.68 (121%) | +268% | cijena +268% vs sredina fer-zone (prag ±40%)<br>raspon sidra 121% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: multiples_relative +545% vs primarno sidro<br>nekonzistentno sidro: ev_ebitda +285% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **RIVP** | FALI RAST · ODSTUPA OD TRŽIŠTA | 3.94–5.33 (30%) | +80% | cijena +80% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **SPAN** | FALI RAST · ODSTUPA OD TRŽIŠTA | 27.24–36.86 (30%) | +78% | cijena +78% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **TOK** | FALI RAST | 13.67–18.50 (30%) | +6% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda +45% vs primarno sidro<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **UCG** | NEEDS EXTRACTION (discovered) · FALI BROJ DIONICA · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>broj dionica (ni share_classes ni shares_outstanding)<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **ULPL** | NEEDS EXTRACTION (needs_review) · FALI RAST | 137.60–222.51 (47%) | n/p | raspon sidra 47% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda -51% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2024) -> rast se ne izvodi |
| **VLEN** | NEEDS EXTRACTION (needs_review) · FALI RAST | 3.35–4.54 (30%) | n/p | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: ev_ebitda +57% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ZABA** | NEKONZISTENTNO | 19.14–25.42 (28%) | +1% | raspon sidra 28% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: residual_income -52% vs primarno sidro<br>placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi |
| **ZITO** | FALI RAST | 18.16–24.57 (30%) | -14% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |

## Sistemska pristranost
- firmi s valuacijom: 18; iznad zone: 12, ispod: 6
- nema alarma (nijedna strana ne prelazi 70%)
