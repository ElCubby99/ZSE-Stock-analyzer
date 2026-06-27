# Končar (KOEI) — izvori za točku 4 (konsolidirana godišnja izvješća)

Sve je **konsolidirano** (Grupa KONČAR), hrvatska verzija. Primarno s koncar.hr,
mirror na ZSE EHO disclosure portalu (eho.zse.hr).

| Godina | Primarni URL | Mirror (EHO ZSE) |
|--------|--------------|------------------|
| 2023 | https://eho.zse.hr/fileadmin/issuers/KOEI/FI-KOEI-26b6d17c58e5d24666dbc8255aca031b.pdf | (isti EHO/KOEI link) |
| 2024 | https://eho.zse.hr/fileadmin/issuers/KOEI/FI-KOEI-962b2a89874cfc24b05051381efef45a.pdf | (isti EHO/KOEI link) |
| 2025 | https://www.koncar.hr/sites/default/files/dokumenti/financijski-izvjestaji/2026-04/Izvjestaj%20GRUPA%202025_HRV.pdf | (provjeri na eho.zse.hr/KOEI) |

> **ENTITET — ČITAJ:** Ekstraktor uzima brojke doslovno iz dokumenta, pa izvor
> MORA biti Grupa KONČAR (KONČAR-Elektroindustrija d.d., ZSE ticker **KOEI**).
> Za 2024. je raniji "primarni" link s koncar.hr
> (`.../2025-04/Revidirano%20konsolidirano%202024.pdf`) zapravo izvješće
> **Grupe KONČAR – D&ST** (Distributivni i specijalni transformatori, zasebno
> kotirano društvo, ticker **KODT**) — prihodi ~467,5 mil EUR, NE ~1.055,6 mil.
> Zato je za 2024. primaran EHO/KOEI mirror (prijava pod izdavateljem KOEI na
> eho.zse.hr), koji je ispravna Grupa KONČAR (poslovni prihodi ~1.066,2 mil EUR).
> NIKAD ne koristi KODT izvješće kao fallback za KOEI — tiho bi učitalo brojke
> krivog entiteta.

> Napomena: koncar.hr i eho.zse.hr NISU na default (Trusted) egress allowlisti.
> Dohvat radi tek nakon što se u mrežnoj politici okruženja (Custom) dopuste
> `koncar.hr`, `*.koncar.hr`, `*.zse.hr` — i to u NOVOJ sesiji (promjena
> allowlist-a rebuilda cache okruženja). Vidi README, "Runbook za točku 4".

## Cross-check sidra (iz priopćenja — SAMO za validatorov eyes-check, NE za upis)

NIKAD ne upisuj ove brojke ručno — služe samo da na usporednoj tablici odmah
vidimo je li ekstrakcija promašila red veličine / skalu.

| Stavka | 2023 | 2024 | 2025 |
|--------|------|------|------|
| Prihodi od prodaje | ~894,1 mil EUR | ~1.055,6 mil EUR | ~1.320 mil EUR |
| Poslovni prihodi (ukupno) | ~908,0 mil EUR | — | — |
| Neto dobit (izvještajna) | ~70,9 mil EUR | ~164,4 mil EUR | ~222,4 mil EUR |
| EBITDA | ~91,4 mil EUR | — | — |

> 2024 neto dobit: revidirano izvješće navodi **164,4 mil EUR** ("izvještajna
> neto dobit", str. izvještaja poslovodstva). Ranije priopćenje je spominjalo
> ~163,3 mil EUR (preliminarno) — koristi 164,4 kao sidro jer je to revidirana
> brojka koju i ekstrakcija vraća (164.353 tis. EUR).

Izvori priopćenja:
- 2024: koncar.hr/en/news/2024-delivers-consolidated-revenue-over-eur-1-billion-and-eur-1633-million-net-profit
- 2023 / 2025: koncar.hr/hr/vijesti/financijski-rezultati
