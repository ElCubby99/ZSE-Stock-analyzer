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

## Status podataka (2026-07-02)
Peer multipli se IZVODE, ne prepisuju: za {ATGR, PODR, RIVP, PLAG, ARNT} treba
(a) EOD cijena — blokirano (zse.hr 403, rest.zse.hr traži ZSE_API_KEY) i
(b) zadnje godišnje financije — izvješća su dostupna na EHO-u (isti tok kao ADRS/CROS),
    ali API ekstrakcija čeka ANTHROPIC_API_KEY.
`python -m src.peer_multiples ATGR PODR RIVP PLAG ARNT` ispisuje pokrivenost i
medijane čim podaci sjednu; do tada svaki peer izlazi kao SKIP s razlogom.
