# Kako procjenjujemo

*Nacrt za pregled (Boris) — v2.1, 14.07.2026. Izvor: doktrina v2 (docs/) +
stvarno stanje sustava. Sve ispod opisuje ono što sustav RADI; gdje je nešto
tek planirano, tako i piše.*

## Što ovo jest — i što nije

Burzovni list je analitička platforma: za svaku praćenu dionicu Zagrebačke
burze pokazujemo javne podatke, financije iz službenih izvješća i našu
procjenu fer vrijednosti s objašnjenjem kako je nastala. **Ništa od toga nije
preporuka za kupnju ili prodaju, ni investicijski savjet.** Pokazujemo brojke,
metode i pretpostavke — zaključak je uvijek čitateljev.

## Tri pristupa vrijednosti — i zašto svaka firma ima svoje sidro

Vrijednost firme se u praksi mjeri na tri načina:

1. **Prinosni**: koliko vrijedi budući novac koji firma stvara (DCF),
   dividende koje isplaćuje (DDM) ili zarada na vlastitom kapitalu iznad
   zahtijevanog prinosa (opravdani P/B, rezidualni dohodak).
2. **Tržišni**: koliko tržište plaća slične firme — jedna metoda "peer
   usporedba" koja kroz više leća (P/E, EV/EBITDA, EV/EBIT, P/B) uspoređuje
   firmu s usporedivima. Leće su ulazi te metode, ne zasebne metode.
3. **Imovinski**: zbroj vrijednosti dijelova (SOTP) — za holdinge i grupe s
   odvojivim dijelovima.

Nijedan pristup nije univerzalno najbolji — zato svaka **vrsta** firme ima
svoje **sidro** (glavnu metodu), a ostale služe kao kontrola:

- **Holding** (npr. Adris, Končar): vrijednost čine udjeli u drugim firmama →
  sidro je **zbroj dijelova**. Kćeri s vlastitom pouzdanom analizom ulaze po
  našoj procjeni, ostale po tržišnoj cijeni — obje brojke su uvijek prikazane.
- **Banka / osiguratelj**: posao je zarađivati na kapitalu → sidro je
  **povrat na kapital** (opravdani P/B, rezidualni dohodak).
- **Industrijalac s ugovorenim poslom** (backlog, guidance): sidro je **DCF**
  s rastom izvedenim iz tog signala.
- **Industrijalac bez forward signala**: sidro je **peer usporedba**.
- **Ciklična firma** (niska profitabilnost kapitala, poluga): oprezno —
  guidance-DCF ako uprava daje brojke, inače knjiga kapitala; EV/EBITDA se
  izbjegava jer laska zaduženim firmama s visokom amortizacijom.
- **Turizam**: sektor se uspoređuje po EV/EBITDA (uz napomenu o najmovima).

Fer-zona = **sidro ± osjetljivost na ključnu pretpostavku** (npr. trošak
kapitala ±1 postotni bod) — a ne raspon svih metoda, jer bi jedna slaba
metoda razvukla zonu u beskorisno.

## Kako biramo parametre

- **Trošak kapitala (r)** — prinos koji ulagač razumno traži: nerizična
  stopa (prinos hrvatske 10-godišnje obveznice) + beta × premija rizika
  tržišta (Damodaranova metodologija za Hrvatsku). *Planirano, još nije
  aktivno: izvoznicima koji većinu prihoda ostvaruju na razvijenim tržištima
  pripada niži country-risk — ponderirat ćemo premiju po geografiji prihoda.*
- **Beta disciplina** — beta se **mjeri** iz burzovne serije svake dionice
  (tjedni prinosi vs CROBEX, 2 godine); gdje je serija prekratka ili
  nelikvidna, koristi se 1,0 i to je jasno označeno kao pretpostavka.
- **Dugoročni rast (g)** — vezan uz gospodarstvo, ne uz želje: 4% nominalno
  za DCF terminal (realni rast + inflacija), konzervativnijih 2,5% za
  kapitalne metode. Nijedna firma ne može "zauvijek" rasti brže od
  gospodarstva u kojem posluje.
- **Peeri** — medijan stvarnih multipla usporedivih firmi s ZSE, istog
  sektora (auto-dijelovi se ne uspoređuju s prehranom); gdje sektorskih peera
  na ZSE nema, metoda nosi nisku pouzdanost i NE sidri zonu. *Planirano:
  europski sektorski medijani uz korekciju za veličinu i likvidnost.*
- **Diskonti se mjere, ne pretpostavljaju** — lekcija Berkshirea (trguje bez
  popusta ili uz premiju) i europskih holdinga (20–40%): popust ovisi o
  firmi. Za Adris smo izmjerili vlastiti povijesni odnos cijene i vrijednosti
  dijelova — pokazuje premiju, pa popust ne primjenjujemo; integrirani parent
  poput Končara (kontrola + ista djelatnost) dobiva 0–5%; default 15–25%
  koristi se samo gdje mjerenje nije moguće, uz jasnu oznaku.

## Rast: čitamo izvješće, ne povijest

Prosjek prošlih godina je loš prognozer: firma s rekordnim backlogom raste
brže od svoje povijesti, a banka s regulatornim ograničenjima sporije. Zato
rast eksplicitne faze (prvih 5 godina) izvodimo iz **forward signala u
zadnjem izvješću** — ugovoreni neizvršeni poslovi (backlog) i njihov trend,
book-to-bill, brojčani guidance uprave — svaki s citatom stranice izvješća.
Pravila su mehanička i konzervativna: brojčani guidance uprave se poštuje;
kvantificirani backlog ograničava rast na ostvareni tempo; samo kvalitativni
signali dobivaju najviše 8%; bez signala se rast ne izmišlja. Povijesni
prosjek ostaje na stranici kao kontekst.

## Kako se čuvamo grešaka

- **Validacije na ulazu**: bilanca se mora zatvarati, dobit matice + manjine
  mora dati ukupnu dobit, EBITDA = EBIT + amortizacija — izvješće koje ne
  prođe ne ulazi u analizu.
- **Identitet roditelj = zbroj dijelova**: kod holdinga svaka stavka (udjel ×
  vrijednost, gotovina, dug, popust) mora biti vidljiva u tablici i zbrojiti
  se u sidro; nemoguć zbroj = crvena zastavica i analiza se zadržava.
- **QA zastavice**: metode koje se ne slažu, široka zona, veliko odstupanje
  od tržišta — sve se loggira i prikazuje, ne skriva.
- **"Što cijena implicira"**: kad je naša zona daleko od tržišne cijene
  (>40%), izračunamo koji rast ili multipl cijena implicira i usporedimo s
  forward signalom — pa napišemo je li razlika plauzibilna ili upitna. To je
  usporedba implikacija, ne presuda o tržištu.
- **Konzervativnost jednom**: oprez se primjenjuje na jednom mjestu, ne
  slaže se u slojeve (npr. popust se ne dodaje na već konzervativne procjene
  kćeri).

## Evolucija i priznate greške

Metodologiju razvijamo javno i s verzijama — i bilježimo što je bilo krivo:

- **v1 (lipanj–početak srpnja 2026.)**: fer-zona je bila raspon svih metoda,
  rast se izvodio iz povijesnog prosjeka (ili nikako), peer multipli su bili
  placeholderi. Posljedica: **sustavno podcjenjivanje rasta** — u jednom
  trenutku je 78% praćenih dionica "trgovalo iznad fer-zone", što je bio
  signal greške u modelu, ne u tržištu.
- **v2 (12.–13.07.2026.)**: rast iz forward signala izvješća (backlog,
  guidance) umjesto povijesti; peer multipli kalibrirani iz baze; zona =
  sidro ± osjetljivost; taksonomija diskonta (integrirani parent bez popusta,
  izmjereni P/NAV); tri pristupa umjesto "zoološkog vrta" metoda; crvena
  pravila koja zadržavaju analizu dok se problem ne riješi.
- **v2.1 (14.07.2026.)**: pokrivenost cijele burze standardiziranim
  obrascima, dividendni kalendar iz službenih stranica papira, ovaj sloj
  transparentnosti (povijest promjena procjene po dionici).

Nismo nepogrešivi ni sada — zato svaka dionica ima vidljivu povijest
promjena svoje zone s razlogom, a distribuciju naših zona prema tržištu
mjerimo kontinuirano (alarm ako >70% završi na istoj strani).

## Automatizacija

Analize generira automatizirani sustav uz ljudski nadzor: podaci dolaze iz
službenih izvora (ZSE, EHO registar izvješća), svaka brojka nosi izvor
(dokument + stranicu), a izvješća koja ne prođu validaciju ostaju izvan
analize dok ih ne pregledamo. Sustav ne piše preporuke — po dizajnu.
