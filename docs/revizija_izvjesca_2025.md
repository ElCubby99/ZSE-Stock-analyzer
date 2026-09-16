# Revizija rundi naspram STVARNIH godišnjih izvješća (FY2025)

Povod: 16. 9. 2026. cijela SNBA runda raspravljala je o „nerazloženih ~23,5
mil. €" dobiti. U revidiranom izvješću ta stavka ima ime, iznos i uzrok.
Uzrok nije bio nedostatak pameti nego nedostatak ulaza — agenti su radili
nad našim agregatima, a agregati tu stavku ne prikazuju.

Zbog toga je prođena SVAKA firma koja ima raspravu. Ovaj dokument je zapis
tog prolaza: što je pronađeno, što je ispravljeno i što je provjereno pa
ostavljeno kako jest. Alat: `src/report_facts.py`,
`scripts/audit_report_facts.py` (revizija se može ponoviti u svakom trenutku).

Pravilo koje iz ovoga slijedi zapisano je u `CLAUDE.md`.

## Ispravljene runde

| Firma | Nalaz | Iznos | Udio | Izvor |
|---|---|---|---|---|
| **SNBA** | prvo konsolidiranje stečene Solvera stambene štedionice d.d.; „Ostali prihodi iz redovnog poslovanja" | 0,35 → 23,72 mil. € | 99,5 % rasta dobiti prije poreza | GFI 2025., oznaka KD |
| **PODR** | dobit od povoljne kupnje (šest poljoprivrednih društava Fortenova grupe, 31. 1. 2025.) | 57,53 mil. € | 87 % razlike izvještajne i normalizirane dobiti | str. 274, ključno revizijsko pitanje |
| **RIVP** | porezna stavka iz troška u prihod — priznavanje poreznih poticaja za ulaganja u turizmu | −4,17 → +9,40 mil. € (poticaji 17,97) | 61 % rasta neto dobiti | bilj. 12 |

Zajedničko im je da su omjeri koje su agenti koristili (P/E, ROE,
pokrivenost dividende) mjerili godinu s jednokratnom stavkom, a runde su ih
čitale kao ponovljivu izvedbu.

## Provjereno, bez potrebe za ispravkom

| Firma | Nalaz | Zašto ne mijenja rundu |
|---|---|---|
| KOEI | dobit od povoljne kupnje 1,25 mil. € (Novi Feromont d.o.o.) | 0,6 % operativne dobiti (213,0 mil. €) |
| KODT | ista transakcija, 1,25 mil. € | 0,7 % EBIT-a (168,3 mil. €); izvješće samo kaže da je jednokratna |
| ZITO | dobit od povoljne kupnje 2,91 mil. € | 6,0 % EBIT-a (48,2 mil. €); izvješće je navodi u vlastitoj tablici jednokratnih stavki |
| ADPL | neto dobit +569 % | operativni oporavak s niske baze: EBITDA 18,4 → 31,1 mil. €, dobit prije poreza 3,7 → 17,4; efektivna porezna stopa 30,0 % → 9,8 % zbog udjela u dobiti pridruženog društva. Bez jednokratne dobiti. |
| ADRS2 | jednokratne stavke SMANJUJU dobit | izvještajna 105 mil. € naspram 109 mil. € iz redovnog poslovanja (otpisi uz novi investicijski ciklus u turizmu) — smjer je konzervativan |
| ATGR | jednokratne stavke smanjuju EBITDA | +9,3 % izvještajno naspram +13,8 % prilagođeno |
| HT | pripajanje HT Servisi d.o.o. | izvješće izričito kaže da transakcija NIJE poslovna kombinacija po MSFI 3 — ne priznaju se ni goodwill ni dobit od povoljne kupnje; učinci idu u kapital, ne u račun dobiti. Vlastite jednokratne stavke (otpremnine, sporovi) smanjuju EBITDA. |
| ZABA, HPB | nema naznaka jednokratnih stavki | dobit +2,9 % odnosno −20,1 %; GFI obrazac priložen kao PDF |
| IKBA, KBZ, PDBA | GFI obrazac strojno pročitan | opseg nepromijenjen, bez velikih „ostalih" stavki |

## Što revizija i dalje NE može sama

Izvješće koje nije GFI obrazac (PDF ili ESEF/iXBRL paket) ne čita se
strojno. Za takva izvješća revizija vraća status `nije_strojno_citljivo`
odnosno `djelomicno`, popis naznaka iz teksta i izvod s brojem stranice —
nikad „uredno". Nalazi iz gornje tablice za te firme dobiveni su ČITANJEM
izvještaja, ne parsiranjem, i zato su ovdje zapisani s brojem stranice.

Status po formatu (FY2025): GFI obrazac imaju IKBA, KBZ, PDBA i SNBA;
ostali su PDF, a HT je ESEF paket.
