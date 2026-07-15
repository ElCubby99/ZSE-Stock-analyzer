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
