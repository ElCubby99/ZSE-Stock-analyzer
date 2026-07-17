# CLAUDE.md — pravila za rad u ovom repozitoriju

## Milestone workflow (obavezno)

Na kraju svakog milestonea, **ako svi testovi prolaze** (pytest + eventualni
Playwright acceptance testovi milestonea), **mergaj radnu granu u `main` i
pushaj** — Vercel deploya automatski s `main`. Redoslijed:

1. Završi milestone na radnoj grani: commit + push (standardni footer).
2. Pokreni testove; ako išta padne, popravi PRIJE mergea — na `main` ne ide
   crveno stanje.
3. `git checkout main && git merge <radna-grana> && git push origin main`
   (fast-forward kad je moguće), pa se vrati na radnu granu.

## Ostala trajna pravila projekta

- **Ništa izmišljeno; n/p nije 0** — prazno polje s razlogom je uvijek bolje
  od krive brojke; parseri imaju stroge gateove (radije preskoči s razlogom).
- **MAR-safe**: bez preporuka, rejtinga i ciljnih cijena; pozicija cijene
  naspram fer-zone je činjenica, zaključak je čitateljev.
- **Svaka brojka nosi izvor** (dokument + stranica / URL) — u bazi i na webu.
- Javni tekstovi **ne referenciraju interne datoteke** (.py, docs/…) —
  upute vode na Metodologiju ili pretpostavke na stranici.
- `ANTHROPIC_API_KEY` živi u gitignoranom `.env` i nikad se ne ispisuje;
  API potrošnja ide kroz `src/api_usage.py` (mjesečni budžet, digest).
- Jezik weba i svih UI tekstova: hrvatski. Dizajn: IBM Plex,
  oxblood/steel/pine (#9E2B25 / #2F5D86 / #1F6E5A).
- Analitika se učitava isključivo kroz consent sustav (Consent Mode v2);
  GTM container i politika kolačića moraju ostati usklađeni — promjena
  kategorija kolačića = bump `CONSENT_VERSION` + ažuriranje politike.
- **i18n (M38): svaki novi user-facing string ide kroz i18n rječnik**
  (`frontend/src/i18n/strings.mjs`, ključ s OBA jezika) uz pojam u
  `docs/glossary_hr_en.md`; **svaka nova ruta registrira HR i EN par u
  registryju** (`en: {path, seo}`); content-marker testovi se izvršavaju
  za oba jezika; formatiranje brojeva/valute/datuma ISKLJUČIVO kroz
  `frontend/src/format.js` (locale iz rute). PR koji doda hardkodirani
  string ili rutu bez para ne prolazi (tests/test_i18n.py).
- **Svaka nova javna stranica/ruta ide isključivo kroz
  `frontend/src/routes/registry.mjs`** — nikad hardkodirana zasebno u
  routeru (main.jsx) i zasebno u sitemap generatoru (prerender.mjs); oba
  čitaju samo registry. `indexable: false` automatski znači noindex + nema
  u sitemapu. Sitemap test (`tests/test_sitemap.py`, traži buildan
  `frontend/dist`) mora ostati zelen prije svakog mergea u `main`.
