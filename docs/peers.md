# Peer skupovi za ADRS i CROS (KORAK 2C)

Korisnik je odluku o peer skupu delegirao modelu ("stavi Claude modelu da odluči").
Ovo je ta odluka s kriterijima; mehanika izvođenja multipla je `src/peer_multiples.py`
(medijan P/E, P/B, EV/EBITDA iz baze — cijene + zadnje godišnje konsolidirane financije).

## Kriteriji
1. Uvrštenost i likvidnost na ZSE ispred "savršene" sektorske podudarnosti —
   multipl izveden iz nelikvidne/nedostupne dionice je gori od šireg peera.
2. Bez cirkularnosti: društva pod kontrolom subjekta vrednovanja NISU peeri
   (MAIS je 93,5% ADRS-ov → ide u SOTP kao tržišna vrijednost udjela, ne u peer skup).
3. Za holding se multipl gleda i po segmentima (turizam zasebno) jer čisti
   "holding peer" na ZSE ne postoji.

## ADRS (Adris grupa — holding: turizam, osiguranje, akvakultura)
| Ticker | Tvrtka | Zašto |
|--------|--------|-------|
| ATGR | Atlantic Grupa | diverzificirana ZSE grupa, najbliži "konglomerat" peer |
| PODR | Podravka | diverzificirana prehrambena grupa, sličan profil discipline kapitala |
| RIVP | Valamar Riviera | najveći ZSE turistički operater — sidro za turistički krak |
| PLAG | Plava Laguna | turizam, usporediv obalni hotelski portfelj |
| ARNT | Arena Hospitality | turizam, hotelski portfelj (dodatna točka za medijan) |

- **Isključeno:** MAIS (ovisno društvo — cirkularno), HT/KOEI (druge industrije bez veze
  s ADRS-ovim segmentima).
- Turistički podskup {RIVP, PLAG, ARNT} služi i kao sanity za `default_multiple`
  EV/EBITDA neuvrštenih turističkih dijelova (HUP-Zagreb) u SOTP-u.

## CROS (Croatia osiguranje — kompozitni osiguratelj)
Na ZSE **ne postoji** drugi uvršteni osiguratelj usporedive veličine ⇒ domaći peer
skup nije moguć. Regionalni uvršteni osiguratelji (namjera, kad izvor podataka bude
dostupan — nisu na ZSE/EHO pa ih trenutna mrežna politika ne pokriva):

| Ticker | Burza | Tvrtka |
|--------|-------|--------|
| ZVTG | Ljubljana | Zavarovalnica Triglav |
| POSR | Ljubljana | Sava Re |
| PZU | Varšava | PZU Group |
| VIG | Beč | Vienna Insurance Group |
| UQA | Beč | Uniqa |

- Dok se njihovi podaci ne mogu dohvatiti, `Params.peer_pe/peer_pb` za CROS **ostaju
  placeholder** (označeno `placeholder=True`), a težinu nose metode koje peer skup ne
  trebaju: opravdani P/B iz vlastitog ROE-a i DDM iz stvarnog dps-a.
- EV/EBITDA za CROS ionako je zabranjen gate-om (financijski sektor).

## Status podataka (2026-07-03) — IZVEDENO
FY2025 konsolidirane financije svih 5 peera ingestane (filinzi 9–13; 4×VALIDATED,
ATGR needs_review na jednoj sporednoj stavci), cijene 02.07.2026 u prices_eod:

| Ticker | P/E | P/B | EV/EBITDA | Napomena |
|--------|-----|-----|-----------|----------|
| ATGR | 20,93 | 1,43 | 7,74 | 13.337.203 dionice (AR2025 bilj. 22, str 189) |
| PODR | 8,20 | 1,53 | 6,24 | 7.120.003 dionice (AR str 347) |
| RIVP | 23,64 | 3,26 | — | 126.027.542 (AR str 216); P/B na equity_parent |
| PLAG | 13,09 | 2,09 | 9,16 | 2.197.772 redovnih − 2.346 trez.; povlaštene (420.000) isključene — nema cijene, fiksna div 0,03 € (AR str 148/203/216) |
| ARNT | 13,69 | 0,96 | 9,59 | 5.128.721 (AR str 93) |

**MEDIJAN: P/E=13,69 (n=5), P/B=1,53 (n=5), EV/EBITDA=8,45 (n=4)** → u
`Params` za ADRS kroz `src/params_calibrated.py` (peers_calibrated=True).
Nijedan peer nije isključen: svi profitabilni; ATGR/PODR diverzificirane
konzumerske grupe (konglomeratski profil), RIVP/PLAG/ARNT turizam (najveći
ADRS-ov krak). CROS peer multipli i dalje placeholder (vidi gore — nema
usporedivog osiguratelja na ZSE; regionalni nedostupni mrežnom politikom).
