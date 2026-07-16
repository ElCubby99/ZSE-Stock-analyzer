# Kako procjenjujemo

*Sve ispod opisuje ono što sustav stvarno radi; gdje je nešto tek planirano,
tako i piše.*

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

- **Trošak kapitala (r) — puni raspis (v3)**: r = rf + β × ERP + CRP
  (+ premija nelikvidnosti). Komponente: **rf** je bezrizični prinos u
  euru (10-godišnji njemački Bund) — namjerno NE hrvatska krivulja, jer
  ona već nosi hrvatski spread; **ERP** je Damodaranova premija zrelog
  tržišta (bez premije zemlje); **CRP** je mala, zasebna premija rizika
  Hrvatske primjerena investment-grade eurozoni ('A-'/A3), ograničena na
  ≤ 1,5 postotna boda i dodana točno jednom (ne množi se betom). Rizik
  zemlje se time računa na JEDNOM mjestu — do metodologije v3 bio je
  nenamjerno uračunat dvaput (u nerizičnoj stopi i unutar premije
  tržišta), što je sustavno snižavalo procjene; vidi „Priznate greške".
  Svaka komponenta na stranici dionice nosi vlastiti izvor i datum unosa.
  *Planirano, još nije aktivno: izvoznicima koji većinu prihoda ostvaruju
  na razvijenim tržištima pripada niži CRP — ponderirat ćemo premiju po
  geografiji prihoda.*
- **Beta disciplina (v2.2)** — regresijska beta iz burzovne serije (tjedni
  prinosi vs CROBEX) koristi se **samo iznad praga likvidnosti** (≥60%
  trgovanih dana i ≥1.000 € prosječnog dnevnog prometa) jer rijetko
  trgovanje statistički obara betu i umjetno uljepšava procjenu
  (stale-price bias). Iznad praga primjenjuje se Blumeova prilagodba
  (0,67·β + 0,33·1); ispod praga ili bez serije koristi se **sektorska
  beta** (Damodaran, Europa), relevered s polugom firme gdje je dug
  poznat. Finalna beta je ograničena na raspon **[0,7, 1,8]**. Porijeklo
  bete (regresija / sektorska / clamp) je vidljivo uz svaku procjenu.
- **Premija nelikvidnosti (v2.2)** — dionicama ispod praga likvidnosti na
  trošak kapitala dodaje se +1,0 do +2,0 postotna boda (stupnjevano po
  likvidnosti): izlazak iz slabo trgovane pozicije nosi stvaran trošak.
  Prikazana je kao zasebna komponenta u pretpostavkama.
- **Svježina ulaza — TTM (v3)**: gdje firma objavljuje kvartalne izvještaje,
  zarada, prihodi i ROE računaju se na **zadnjih 12 mjeseci** (zadnje
  godišnje + ovogodišnji kvartali − lanjski kvartali; kvartalni izvještaji
  su kumulativni i nerevidirani). Strogi gateovi: ako je kvartalna serija
  nekonzistentna s revidiranim godišnjim izvješćem (odstupanje > 5%) ili
  nema lanjske usporedbe, TTM se NE gradi — koristi se godišnje uz vidljivu
  oznaku `godišnji podatak` s razlogom. Bilančne stavke (kapital, dug)
  uzimaju se sa zadnjeg objavljenog datuma.
- **Faza rasta (g1) — isključivo iz objavljenih brojki (v3)**: g1 =
  min(trogodišnji CAGR prihoda — odnosno zarade gdje prihodna serija ne
  postoji — iz naše baze, **cap 10%**), pa linearni fade prema terminalnom
  g kroz 5 godina. Gdje trogodišnje serije nema: min(rast zadnjih 12
  mjeseci naspram prošle godine, **cap 8%**) uz oznaku `kratka serija`.
  Ručne "forward procjene" (backlog, guidance, očekivanja uprave) se za
  stopu rasta **ne koriste** — brojčani guidance smije poslužiti jedino
  kao zamjenski ulaz za novčani tok kad izvještaj o novčanom toku nije
  objavljen, i tada je jasno označen.
- **ROE za kapitalne metode (v3)**: koristi se **viši od (trogodišnji
  medijan godišnjih ROE, TTM ROE × 0,9)** — medijan stabilizira jednu
  netipičnu godinu (npr. COVID ili jednokratni dobitak), a faktor 0,9
  zadržava oprez prema svježoj, nerevidiranoj brojci. Bez kvartala:
  godišnji ROE.
- **Dugoročni rast (g)** — vezan uz gospodarstvo, ne uz želje: 4% nominalno
  za DCF terminal (realni rast + inflacija), konzervativnijih 2,5% za
  kapitalne metode. Nijedna firma ne može "zauvijek" rasti brže od
  gospodarstva u kojem posluje.
- **Fer-zona = medijan kvalificiranih metoda (v3)**: zona više nije raspon
  jedne "glavne" metode. Kvalificirana je svaka metoda s pozitivnom
  vrijednošću, dovoljnom pouzdanošću ulaza i stabilnom osjetljivošću;
  sredina zone je **medijan** njihovih vrijednosti, a širina dolazi iz
  osjetljivosti primarnog sidra (r ± 1 postotni bod). Ako se dvije metode
  međusobno slažu (±20%) a dosadašnje sidro od njih bitno odstupa (>30%),
  sidro gubi primat — to je vidljivo zabilježeno uz procjenu.
- **Test održive dividende (v3)**: za isplatitelje dividendi zona mora
  proći unutarnju kontrolu — prinos iz **održive** dividende na donjem rubu
  zone ne smije biti veći od r − g (Gordonova donja granica: ako sama
  dividenda na nekoj cijeni nosi više nego što ulagač traži za rizik, ta je
  cijena preniska da bi bila fer). U pragu se koristi ista stopa rasta
  kojom je zona i izračunata (2,5% za kapitalne metode, 4% za DCF/DDM
  sidra) — prag s drugačijom stopom lažno bi pobijao zonu zbog razlike
  naših vlastitih pretpostavki. Zona koja test ne prolazi nosi oznaku
  **"u rekalibraciji"** i ne prikazuje se kao mjerodavna dok se ulazi ne
  razriješe; puni raspis testa s brojkama te dionice stoji na njezinoj
  stranici. Analogno postoji i obrnuti test (previsoka zona uz payout
  ~100%).
- **Zanemariv free float (v3)**: kad top-10 dioničara drži >90% (npr.
  INA), cijena se formira u zanemarivom prometu pod dominantnim vlasnicima
  — raskorak cijene i zone tada NIJE informativan, nosi istaknutu napomenu
  i ne ulazi u agregat "temperatura tržišta".
- **Klase dionica — jedna vrijednost firme (v3)**: kod firmi s dvije
  klase (redovne i povlaštene: ADRS/ADRS2, KODT/KODT2, CROS/CROS2,
  PLAG/PLAG2) fer-zona se računa za FIRMU, pa raspoređuje na klase
  **tržišno opaženim omjerom cijena klasa** — medijanom dnevnog omjera
  kroz zadnjih 5 godina, samo na danima kad su obje klase stvarno
  trgovane (najmanje 30 opažanja; inače omjer dividendnih prava uz oznaku
  `teorijski omjer`). Premija redovne dionice postoji jer redovna nosi
  pravo glasa, a povlaštena ga nema — koliko to pravo vrijedi ne izvodimo
  teorijski (ovisi o vjerojatnosti preuzimanja, koncentraciji vlasništva i
  likvidnosti), nego uzimamo koliko ga tržište POVIJESNO plaća. Obje klase
  tako imaju zone izvedene iz iste vrijednosti firme: ne može jedna biti
  "u zoni" a druga duboko iznad, osim ako današnji omjer klasa odstupa od
  povijesnog medijana — a tada je upravo TA razlika činjenica koju
  prikazujemo.
- **Dividende — klasifikacija isplata i održiva dividenda (v3)**: svaka
  povijesna isplata nosi činjeničnu oznaku tipa — **redovna**;
  **izvanredna** (iznos veći od 150% medijana prethodnih redovnih isplata
  te klase); **iz zadržane dobiti** (ukupna isplata firme veća od neto
  dobiti fiskalne godine iz koje se isplaćuje); formulacija same objave
  (npr. "izvanredna dividenda") ima prednost pred ovim pravilima.
  **Postotak dobiti** se računa isključivo prema dobiti pripadne fiskalne
  godine — ako ta godina nije u bazi, polje je prazno (nikad kriva
  godina). **Očekivana održiva dividenda**: D_sust = održivi payout ×
  normalizirana dobit (zadnjih 12 mjeseci) / broj dionica; održivi payout
  je objavljena politika društva (kad postoji i kad je pokrivena tekućom
  dobiti), inače medijan povijesnih payout omjera računan SAMO nad
  redovnim isplatama — jednokratne isplate ne ulaze u bazu. Kod banaka
  payout iznad 80% nosi napomenu o regulatornom odobrenju, a za održivu
  bazu koristi se najviše 70%. **Pokrivenost najave** = normalizirana
  dobit / najavljena isplata; ispod 1,2 isplata je označena kao "napeto
  pokrivena", ispod 1,0 najava se ne koristi u procjeni. Dividendni
  diskontni model računa nad D_sust — nikad nad sirovom zadnjom isplatom.
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
- **v3 — faza S (16.07.2026.)**: klase dionica — priznata greška: obje
  klase iste firme uspoređivale su se s JEDNOM zonom, pa je redovna
  (s premijom glasa) izgledala "+58% iznad" dok je povlaštena bila "u
  zoni" — ista firma, dvije priče. Novo: vrijednost firme se raspoređuje
  na klase tržišnim medijanom omjera cijena; svaka klasa ima svoju zonu.
- **v3 — faza A (16.07.2026.)**: triangulacija umjesto dogme jednog sidra —
  priznata greška: fer-zona je bila raspon JEDNE metode po tipu firme, pa
  su potvrde koje konvergiraju prema drugačijoj vrijednosti bile vidljive
  ali bez utjecaja (Croatia osiguranje: dividendni model, rezidualni
  dohodak i peer usporedba stajali su 40–120% iznad sidra), a promjena
  sidra znala je preko noći prebaciti dionicu s "duboko iznad" na "duboko
  ispod" zone (Podravka). Novo: zona = medijan kvalificiranih metoda,
  vidljivo demote pravilo, test održive dividende s oznakom
  "u rekalibraciji" i napomena o zanemarivom free floatu.
- **v3 — faza DIV (16.07.2026.)**: održiva dividenda — priznata greška:
  dividendni model je računao nad sirovom zadnjom isplatom, pa bi
  jednokratna isplata (npr. iz zadržane dobiti) lažno podigla procjenu, a
  propuštena godina lažno je srušila. Novo: klasifikacija svih povijesnih
  isplata (redovna / izvanredna / iz zadržane dobiti, s "% dobiti" prema
  točnoj fiskalnoj godini), očekivana održiva dividenda D_sust (održivi
  payout × normalizirana dobit) i pokrivenost najave — model računa nad
  D_sust, jednokratne isplate ne ulaze u bazu.
- **v3 — faza G (16.07.2026.)**: TTM i rast iz podataka — priznata greška:
  sve se vrednovalo iz zadnjeg GODIŠNJEG izvješća iako za većinu firmi u
  bazi postoje kvartali, a kapitalne metode (opravdani P/B, rezidualni
  dohodak) nisu imale nikakvu fazu rasta — firme s rastućom dobiti bile su
  sustavno podcijenjene, a jednokratni dobici u prošloj godini precijenjeni.
  Novo: TTM za zaradu/prihode/ROE gdje kvartali postoje (uz stroge gateove
  konzistentnosti), stopa rasta isključivo izvedena iz objavljenih brojki
  (3g CAGR uz cap 10%, odnosno kratka serija uz cap 8% — ručne forward
  procjene ukinute), ROE pravilo max(3g medijan, TTM×0,9). Svaka firma bez
  kvartala nosi oznaku `godišnji podatak`.
- **v3 — faza K (16.07.2026.)**: rekalibracija troška kapitala — priznata
  greška: **rizik Hrvatske bio je uračunat dvaput** — nerizična stopa bila
  je hrvatska 10-godišnja obveznica (koja već nosi hrvatski spread), a
  premija tržišta je dodatno sadržavala premiju zemlje. Uz to je premija
  zemlje bila skrivena unutar premije tržišta umjesto vidljiva. Novi
  raspis: rf = 10g njemački Bund, ERP = zrela premija tržišta, CRP =
  zasebna mala premija Hrvatske (≤ 1,5 p.b., 'A-'/A3 eurozona), premija
  nelikvidnosti samo ispod praga likvidnosti. Učinak: r se uz β=1 spušta
  s 9,31% na 8,13%, fer-zone se pomiču naviše; svaka promjena zabilježena
  u povijesti procjene dionice. Sustavni pregled uzroka: interna
  forenzika v3 (faza D), sažeta u ovom changelogu kroz faze v3.
- **v2.3 (16.07.2026.)**: crveno pravilo za degenerirano sidro — priznata
  greška: sidrena metoda čiji je vlastiti raspon osjetljivosti širi od 100%
  baze (npr. DCF u godini izvanrednog capexa/akvizicije) davala je besmisleno
  široke fer-zone (Podravka: 14–53 € uz potvrdne metode 3–5× više). Takvo
  sidro sada pada na sljedeći pristup u hijerarhiji, ostaje prikazano s
  razlogom isključenja. Namjerno se NE uspoređuje sidro s ostalim metodama
  kao kriterij (kod holdinga SOTP legitimno odstupa od operativnih leća).
- **v2.2 (15.07.2026.)**: disciplina bete — priznata greška: regresijske
  bete nelikvidnih dionica (npr. serija s ~40% trgovanih dana) statistički
  su nepouzdane i umjetno su SNIŽAVALE trošak kapitala. Uvedeni prag
  likvidnosti, sektorske bete (Damodaran), Blumeova prilagodba, granice
  [0,7, 1,8] i premija nelikvidnosti. Učinak: 47 od 64 fer-zona pomaknuto
  (prosječni pomak 20%, pretežno naniže — strože), svaka promjena
  zabilježena u povijesti procjene te dionice.
- **v2.1 (14.07.2026.)**: pokrivenost cijele burze standardiziranim
  obrascima, dividendni kalendar iz službenih stranica papira, ovaj sloj
  transparentnosti (povijest promjena procjene po dionici).

Nismo nepogrešivi ni sada — zato svaka dionica ima vidljivu povijest
promjena svoje zone s razlogom, a distribuciju naših zona prema tržištu
mjerimo kontinuirano (alarm ako >70% završi na istoj strani).

## Obveznice

Za obveznice ne računamo fer-zonu — prikaz je **deterministička analiza
prinosa** iz javnih ulaza (čista cijena sa ZSE, kupon i dospijeće iz
podataka uvrštenja). Nema pretpostavki o rastu ni diskontnim stopama;
svaka brojka slijedi iz formule:

- **Cijene su čiste (clean)**, u % nominale — kako kotiraju na ZSE.
  Obveznicama se trguje rijetko, pa je cijena često stara: takva nosi
  ILIKV. oznaku i indikativna je, kao i kod dionica.
- **Tekući prinos** = godišnji kupon / čista cijena.
- **Obračunata kamata** (ACT/ACT ICMA): kupon/frekvencija × dani od
  zadnjeg kupona / dani u kuponskom razdoblju. Konvencija dana i
  frekvencija kupona žive u prospektu — dok ih ne potvrdimo iz prospekta,
  koristimo ACT/ACT i godišnji kupon i to OZNAČAVAMO kao pretpostavku.
- **YTM (prinos do dospijeća)**: stopa y za koju je prljava cijena
  (čista + obračunata kamata) jednaka zbroju diskontiranih budućih
  isplata: Σ CF/(1+y)^t, gdje su t vremena do isplata u godinama
  (ACT/365,25), a raspored isplata se izvodi unatrag od dospijeća.
  Rješavamo bisekcijom (deterministički, bez lokalnih minimuma);
  settlement za izračun je datum zadnje cijene.
- **Duracija**: Macaulayjeva = Σ t·PV(CF)/Σ PV(CF); modificirana =
  Macaulayjeva / (1+y). Mjera osjetljivosti cijene na promjenu prinosa.
- Izdavatelji bez determinističkog izvora imena nose status
  **"master data u obradi"** — ništa se ne izmišlja; YTM se ne prikazuje
  bez potpunih ulaza (kupon + dospijeće + cijena).

## Odakle podaci

Sažetak izvora — svaki tip podatka na webu ima poznato porijeklo i deklariranu
svježinu (provjereno 15.07.2026.):

- **Cijene**: službena ZSE tečajnica (EOD JSON); ažurira se radnim danom
  nakon zatvaranja trgovine (16:00), a uz svaku cijenu stoji stvarni datum
  podatka. Povijest po papiru iz ZSE arhive. Nelikvidne dionice nose oznaku
  uz cijenu.
- **Financijska izvješća**: EHO registar propisanih informacija (službene
  objave izdavatelja, PDF/XLSX). Standardizirane obrasce (TFI-POD, nadzorni
  obrazac banaka, FINREP, ISD osiguranja) čitaju deterministički parseri s
  provjerom AOP oznake i naziva retka; što ne prođe validaciju, ne ulazi u
  analizu. Svaka brojka nosi dokument i stranicu.
- **Dividende**: ZSE stranica papira (iznos, ex-datum, record, isplata) +
  službene objave prijedloga. Prijedlog nije isplata — status je uvijek
  vidljiv.
- **Broj dionica / ISIN**: ZSE stranica papira (uvrštena količina, klase);
  trezorske dionice iz bilješki godišnjih izvješća.
- **Dioničari (top 10)**: ZSE stranica papira (izvor SKDD; lista bez
  objavljenog as-of datuma — vodimo je s datumom dohvata) + tablice
  najvećih dioničara iz godišnjih izvješća (s citatom stranice). Skrbnički
  i zbirni računi su označeni — nisu stvarni krajnji vlasnici. Promjene
  prikazujemo samo kad postoje dva snapshota; imena isključivo kako su
  javno objavljena.
- **Nerizična stopa i premija rizika**: prinos HR 10-godišnje državne
  obveznice + Damodaranova premija za Hrvatsku; ručno kalibrirano s citatom
  u svakoj valuaciji, revidira se pri svakoj rekalibraciji.
- **Peer multipli**: izračun iz vlastite baze (ZSE firme s validiranim
  financijama), kriteriji peer skupova javno u dokumentaciji; sektor bez
  usporedivog peera ne dobiva peer-metodu.

Detaljni registar izvora (način čitanja, poznate slabosti svakog izvora,
datumi provjere) vodi se u internoj projektnoj dokumentaciji i redovito se
revidira.

## Česta pitanja

**Što je fer-zona?** Raspon vrijednosti po dionici koji proizlazi iz naših
metoda vrednovanja (sidrena metoda po arhetipu firme ± osjetljivost na ključne
pretpostavke). Nije ciljna cijena — činjenični je prikaz što fundamenti govore
uz javno ispisane pretpostavke.

**Kako se fer-zona računa?** Svaka firma dobiva arhetip (banka, industrija,
holding…) koji određuje sidrenu metodu (npr. rezidualni dohodak za banke,
DCF za operativne firme, SOTP za holdinge). Zona = sidro ± osjetljivost na
ključnu pretpostavku; ostale metode služe kao potvrda. Svi parametri (trošak
kapitala, rast, peer multipli) imaju citiran izvor na samoj stranici dionice.

**Jesu li ovo preporuke za kupnju ili prodaju?** Ne. Servis ne objavljuje
preporuke, rejtinge ni ciljne cijene. Cijena iznad ili ispod zone je
činjenica iz podataka, ne signal — zaključak je uvijek čitateljev. Za
investicijske odluke potražite ovlaštenog savjetnika.

**Zašto neka dionica nema fer-zonu?** Zona se objavljuje samo kad podaci
prođu validaciju. Ako izvješća nedostaju ili ne prođu provjere, prikazujemo
samo tržišni profil — polja ostaju prazna (n/p), ništa se ne procjenjuje.

**Koliko su podaci ažurni?** Cijene su službeni EOD zaključci Zagrebačke
burze; ažuriraju se radnim danom nakon zatvaranja trgovine (16:00), a uz
svaku cijenu stoji stvarni datum podatka. Financije se ažuriraju kad
izdavatelj objavi izvješće (EHO registar). Datum stoji uz svaku brojku.

## Automatizacija

Analize generira automatizirani sustav uz ljudski nadzor: podaci dolaze iz
službenih izvora (ZSE, EHO registar izvješća), svaka brojka nosi izvor
(dokument + stranicu), a izvješća koja ne prođu validaciju ostaju izvan
analize dok ih ne pregledamo. Sustav ne piše preporuke — po dizajnu.
