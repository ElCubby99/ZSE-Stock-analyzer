---
title: Zašto holding ne vrijedi kao zbroj svojih dijelova
category: Edukacija
date: 2026-07-14
summary: SOTP metoda zbraja dijelove holdinga, a tržište gotovo uvijek plaća manje od tog zbroja. Što je holding diskont, odakle dolazi i kako se mjeri.
---

## Što je holding i zašto ga je teško vrednovati

Holding je društvo čija se vrijednost ne krije u vlastitom pogonu, nego u
udjelima koje drži u drugim firmama — ponekad u desecima različitih biznisa,
od turizma do industrije. Kad kupujete dionicu holdinga, ne kupujete jedan
posao nego košaricu poslova, plus (ili minus) ono što se nalazi na razini
samog holdinga: novac, dugove i troškove uprave.

Zato se holding ne vrednuje jednim omjerom poput P/E (cijena kroz dobit).
Standardni pristup zove se **SOTP — "sum of the parts"**, doslovno: zbroj
dijelova.

## Kako radi SOTP

Ideja je jednostavna:

- Za svaki udio koji holding drži procijeni se vrijednost — ako je firma
  uvrštena na burzu, uzima se njezina tržišna kapitalizacija (cijena × broj
  dionica) pomnožena postotkom vlasništva; ako nije uvrštena, procjenjuje se
  preko dobiti ili EBITDA-e (dobit prije kamata, poreza i amortizacije —
  gruba mjera operativne zarade).
- Zbroje se svi udjeli.
- Doda se novac na razini holdinga, a odbiju dugovi.

Rezultat je **NAV — neto vrijednost imovine** (net asset value): koliko bi
teorijski vrijedila košarica kad biste je rastavili i prodali dio po dio.

## …i tu nastaje "problem": tržište plaća manje

Gotovo svugdje u svijetu dionica holdinga trguje se **ispod** svog NAV-a.
Razlika se zove **holding diskont** i tipično iznosi 10–30 %. Nije riječ o
grešci tržišta nego o cijeni stvarnih nedostataka:

1. **Ne možete rastaviti košaricu.** Mali dioničar ne može natjerati holding
   da proda udjele i podijeli novac. Vrijednost "na papiru" postoji, ali do
   nje se ne može doći.
2. **Dvostruki trošak.** Uprava holdinga košta, a ispod nje svaka firma ima
   svoju upravu. Taj trošak svake godine jede dio prinosa.
3. **Porez na izlazu.** Kad bi holding prodavao udjele, na dobitke bi platio
   porez — dio NAV-a koji dioničar nikad ne vidi.
4. **Kapital se ne vraća uvijek vlasnicima.** Novac od prodaje jednog udjela
   uprava često uloži u novi projekt umjesto da ga isplati — a novi projekt
   može biti i lošiji od starog.

## Primjer na izmišljenom holdingu

Zamislite Holding X koji drži: 60 % turističke firme čija tržišna vrijednost
udjela iznosi 300 mil. €, 100 % neuvrštenog proizvođača procijenjenog na
150 mil. € i 50 mil. € neto novca. NAV = 300 + 150 + 50 = **500 mil. €**.

Ako se dionice Holdinga X na burzi ukupno vrednuju na 375 mil. €, tržište ga
plaća uz **diskont od 25 %**. To nije ni "jeftino" ni "skupo" samo po sebi —
to je informacija. Pitanja koja iz nje slijede: je li diskont povijesno
uvijek toliki? Mijenja li se? Postoji li razlog da se ikad zatvori (npr.
najava prodaje udjela ili isplate)?

## Kako mi to radimo

Na ovoj platformi holding vrednujemo upravo SOTP metodom, uz dva pravila
koja smatramo poštenima:

- **Diskont se mjeri, ne pretpostavlja.** Gdje povijest cijene i NAV-a
  postoji, računamo koliki je diskont stvarno bio kroz vrijeme i koristimo
  izmjereni raspon. Tek gdje mjerenje nije moguće, koristimo standardni
  raspon i to jasno označimo kao pretpostavku.
- **Integrirani operativni vlasnik nije pasivni holding.** Firma koja
  kontrolira i konsolidira svoje tvrtke u istoj djelatnosti (upravlja njima
  kao jednim poslom) dobiva mali ili nikakav diskont — nedostaci opisani
  gore za nju uglavnom ne vrijede.

Svaka SOTP analiza na stranicama dionica prikazuje raščlambu po dijelovima,
primijenjeni diskont i razlog zašto je baš takav. Primjer je ilustrativan i
ne odnosi se ni na jedno konkretno društvo; ništa u ovom tekstu nije
preporuka za kupnju ili prodaju.
