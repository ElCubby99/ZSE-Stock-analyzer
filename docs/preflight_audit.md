# Pre-flight audit — 2026-07-13

Dijagnoza bez API poziva: baza + javni zse.hr scrape. Odluka o
ekstrakciji je urednička; ovo je popis nalaza, ne plan.

| Ticker | Status | Fer-zona € | Cijena vs zona | Nalazi |
|---|---|---|---|---|
| **ADPL** | FALI RAST | 18.81–26.10 (32%) | +35% | raspon sidra 32% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: comps +133% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ADRS** | ODSTUPA OD TRŽIŠTA | 91.83–96.67 (5%) | +75% | cijena +75% vs sredina fer-zone (prag ±40%) |
| **ARNT** | FALI RAST | 52.99–71.69 (30%) | -34% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ATGR** | FALI RAST · ODSTUPA OD TRŽIŠTA | 23.57–34.07 (36%) | +75% | cijena +75% vs sredina fer-zone (prag ±40%)<br>raspon sidra 36% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **BSQR** | NEEDS EXTRACTION (discovered) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **CROS** | ODSTUPA OD TRŽIŠTA | 1,577.65–2,288.90 (37%) | +72% | cijena +72% vs sredina fer-zone (prag ±40%)<br>raspon sidra 37% > 20% (osjetljivost na r — nije min-max) |
| **CTKS** | NEEDS EXTRACTION (needs_review) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **DLKV** | ODSTUPA OD TRŽIŠTA · FALI RAST | 4.48–5.52 (21%) | +256% | cijena +256% vs sredina fer-zone (prag ±40%)<br>raspon sidra 21% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **HPB** | FALI RAST | 326.65–465.35 (35%) | -16% | raspon sidra 35% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: residual_income -26% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **HT** | FALI RAST · ODSTUPA OD TRŽIŠTA | 20.98–30.59 (37%) | +59% | cijena +59% vs sredina fer-zone (prag ±40%)<br>raspon sidra 37% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **IG** | FALI RAST | 55.87–75.58 (30%) | +9% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2024) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina |
| **KODT** | FALI RAST | 3,355.05–4,110.20 (20%) | +22% | raspon sidra 20% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: comps +258% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **KOEI** | FALI RAST | 797.38–839.35 (5%) | +22% | nekonzistentno sidro: dcf_fcf +33% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **KTJV** | NEEDS EXTRACTION (needs_review) · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **MAIS** | FALI RAST · ODSTUPA OD TRŽIŠTA | 36.61–49.53 (30%) | +52% | cijena +52% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **PLAG** | FALI RAST | 296.07–400.57 (30%) | -2% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **PODR** | ODSTUPA OD TRŽIŠTA · FALI RAST | 23.25–81.77 (111%) | +208% | cijena +208% vs sredina fer-zone (prag ±40%)<br>raspon sidra 111% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: comps +452% vs primarno sidro<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **RIVP** | FALI RAST · ODSTUPA OD TRŽIŠTA | 3.90–5.28 (30%) | +82% | cijena +82% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **SPAN** | FALI RAST · ODSTUPA OD TRŽIŠTA | 31.78–42.88 (30%) | +53% | cijena +53% vs sredina fer-zone (prag ±40%)<br>raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **TOK** | FALI RAST | 10.41–13.99 (29%) | +39% | raspon sidra 29% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: comps +39% vs primarno sidro<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **UCG** | NEEDS EXTRACTION (discovered) · FALI BROJ DIONICA · FALI RAST | n/p | n/p | 3g prihoda (ima 0: ništa) -> rast se ne izvodi<br>broj dionica (ni share_classes ni shares_outstanding)<br>bilanca/RDG: ukupna imovina<br>bilanca/RDG: kapital<br>bilanca/RDG: neto dobit |
| **ULPL** | FALI RAST | 38.36–172.06 (127%) | n/p | raspon sidra 127% > 20% (osjetljivost na r — nije min-max)<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2024) -> rast se ne izvodi |
| **VLEN** | FALI RAST | 1.67–2.25 (29%) | n/p | raspon sidra 29% > 20% (osjetljivost na r — nije min-max)<br>beta=1,0 pretpostavka (nije izmjerena iz serije)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |
| **ZABA** | NEKONZISTENTNO | 19.14–25.42 (28%) | +1% | raspon sidra 28% > 20% (osjetljivost na r — nije min-max)<br>nekonzistentno sidro: residual_income -52% vs primarno sidro |
| **ZITO** | FALI RAST | 17.37–23.50 (30%) | -10% | raspon sidra 30% > 20% (osjetljivost na r — nije min-max)<br>3g prihoda (ima 1: 2025) -> rast se ne izvodi |

## Sistemska pristranost
- firmi s valuacijom: 19; iznad zone: 15, ispod: 4
- ALARM: 79% firmi trguje IZNAD fer-zone (model sustavno PODcjenjuje) — prag 70%
