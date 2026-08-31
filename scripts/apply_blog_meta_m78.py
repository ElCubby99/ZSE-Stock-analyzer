#!/usr/bin/env python3
"""M78 (nalog 30.08.2026., zadatci 2 i 4): naslovi i meta opisi šest blog
tekstova prema GSC nalazu (ETF klaster ~180 impresija / 0 klikova; naslov
ETF bloga nije sadržavao nijedan ticker) + brisanje testnog drafta.

Pokreće se kroz db-sync workflow (input blog_meta=true) nad produkcijom
(ZSE_DSN). Idempotentno: UPDATE po slugu; EN polja se postavljaju SAMO
postovima koji EN verziju već imaju (title_en IS NOT NULL) — "po istom
ključu gdje postoje". content_md se NE dira. IG meta opis ispravlja i
stvarnu grešku (stari je bio odsječen usred riječi: "…Bez preporuk").

Nakon primjene sadržaj na sajt dolazi prvim Vercel buildom (deploy hook
okida daily-eod ili db-sync regen korak).
"""
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

# (slug, title, meta, title_en, meta_en) — meta hard cap 160 (kao endpoint)
POSTS = [
    ("etf-ovi-zagrebacka-burza-troskovi-likvidnost-sastav",
     "7CRO, 7BET, 7POL, 7SLO, 7CASH i 7GROM — svi ETF-ovi na Zagrebačkoj burzi",
     "Svih šest ETF-ova na ZSE: 7CRO, 7BET, 7POL, 7SLO, 7CASH, 7GROM — TER "
     "0,32–0,90 %, likvidnost, sastav i razlika cijene i NAV-a.",
     "7CRO, 7BET, 7POL, 7SLO, 7CASH and 7GROM — every ETF on the Zagreb "
     "Stock Exchange",
     "All six ZSE ETFs: 7CRO, 7BET, 7POL, 7SLO, 7CASH, 7GROM — TER "
     "0.32–0.90%, liquidity, composition and the price-to-NAV gap."),
    ("dividende-zagrebacka-burza-2026-kalendar-ex-datum",
     "Kalendar dividendi 2026 — Zagrebačka burza: ex-datumi, iznosi i prinosi",
     "Kalendar isplate dividendi na ZSE u 2026.: 43 isplate kod 41 "
     "izdavatelja, medijan prinosa 3,13 %, kako radi ex-datum i što znače "
     "oznake.",
     "Dividend calendar 2026 — Zagreb Stock Exchange: ex-dates, amounts and "
     "yields",
     "ZSE dividend payout calendar for 2026: 43 payouts from 41 issuers, "
     "median yield 3.13%, how the ex-date works and what the labels mean."),
    # kako-citati-pe-omjer NIJE u bazi — file-based post; naslov/meta žive
    # u content/blog/kako-citati-pe-omjer.md (+ en/) frontmatteru (M78)
    ("ad-plastik-adpl-prihodi-ebitda-marza-fer-zona",
     "AD Plastik dionica (ADPL): prihodi, EBITDA marža, P/E i fer-zona",
     "AD Plastik (ADPL) dionica: prihodi 2023.–2025., EBITDA marža, P/E 7,5, "
     "P/B 0,94, dividenda i fer-zona. Informativno, nije preporuka.",
     "AD Plastik stock (ADPL): revenue, EBITDA margin, P/E and the "
     "fair-value zone",
     "AD Plastik (ADPL): revenue 2023–2025, EBITDA margin, P/E 7.5, P/B "
     "0.94, dividend and the fair-value zone. Informational, not a "
     "recommendation."),
    ("ing-grad-ig-prihodi-ebitda-dividenda-fer-zona",
     "ING-GRAD dionica (IG): prihodi, marža, dividenda 3,00 € i fer-zona",
     "ING-GRAD (IG) dionica: prihodi rasli 72,9 % u tri godine na 168,4 mln "
     "EUR, marža pada, P/E 15,7, dividenda 3,00 EUR. Informativno, nije "
     "preporuka.",
     "ING-GRAD stock (IG): revenue, margin, €3.00 dividend and the "
     "fair-value zone",
     "ING-GRAD (IG): revenue up 72.9% in three years to €168.4m, margin "
     "declining, P/E 15.7, dividend €3.00. Informational, not a "
     "recommendation."),
    ("burzovni-list-je-online",
     "Što je Burzovni list: fer-zone, pokazatelji i dividende za sve dionice "
     "ZSE",
     "Besplatna analiza svih dionica Zagrebačke burze: fer-zone, financijski "
     "pokazatelji, kalendar dividendi, screener i usporedba. Bez "
     "registracije.",
     "What Burzovni list is: fair-value zones, ratios and dividends for "
     "every ZSE stock",
     "Free analysis of every Zagreb Stock Exchange stock: fair-value zones, "
     "financial ratios, a dividend calendar, screener and comparison. No "
     "sign-up."),
]

TEST_DRAFT_SLUG = "zz-test-update-1788124780905"


def main() -> int:
    for _, t, m, te, me in POSTS:
        assert len(m) <= 160, f"meta > 160: {m!r}"
        assert len(me) <= 160, f"meta_en > 160: {me!r}"
        assert len(t) <= 200 and len(te) <= 200
    with get_conn() as conn, conn.cursor() as cur:
        for slug, t, m, te, me in POSTS:
            cur.execute("""UPDATE blog_posts SET title=%s, meta_description=%s
                           WHERE slug=%s""", (t, m, slug))
            n_hr = cur.rowcount
            cur.execute("""UPDATE blog_posts SET title_en=%s,
                             meta_description_en=%s
                           WHERE slug=%s AND title_en IS NOT NULL""",
                        (te, me, slug))
            print(f"[blog-meta] {slug}: HR {'ok' if n_hr else 'NE POSTOJI!'}"
                  f", EN {'ok' if cur.rowcount else 'preskočen (nema EN verzije)'}")
        # zadatak 4: testni draft (nikad objavljen) se briše
        cur.execute("""DELETE FROM blog_posts
                       WHERE slug=%s AND status='draft'
                         AND published_at IS NULL""", (TEST_DRAFT_SLUG,))
        print(f"[blog-meta] test draft {TEST_DRAFT_SLUG}: "
              f"{'obrisan' if cur.rowcount else 'nije pronađen (već obrisan?)'}")
        conn.commit()
    print("[blog-meta] GOTOVO — na sajt dolazi prvim sljedećim Vercel buildom")
    return 0


if __name__ == "__main__":
    sys.exit(main())
