#!/usr/bin/env python3
"""M66 forenzika: zašto su /vijesti zastarjele iako pipeline javlja dedup?

Čita news_items (ista Supabase baza kao ZSE_DSN) — SAMO ispis, bez pisanja.
Ukloniti kad se uzrok potvrdi i popravi."""
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402


def main() -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT status, count(*) FROM news_items GROUP BY 1""")
        print("po statusu:", cur.fetchall())
        cur.execute("""SELECT source_type, status, count(*),
                              max(published_at)::date, max(created_at)::date
                       FROM news_items GROUP BY 1, 2 ORDER BY 1, 2""")
        for r in cur.fetchall():
            print("tip/status:", r)
        cur.execute("""SELECT id, ticker, category, status,
                              published_at::date, created_at::date,
                              left(headline, 60)
                       FROM news_items ORDER BY created_at DESC LIMIT 12""")
        print("najnovijih 12 po created_at:")
        for r in cur.fetchall():
            print("  ", r)
        cur.execute("""SELECT id, ticker, status, published_at::date,
                              left(headline, 60)
                       FROM news_items WHERE status='published'
                       ORDER BY published_at DESC NULLS LAST LIMIT 8""")
        print("najnovijih 8 PUBLISHED po published_at:")
        for r in cur.fetchall():
            print("  ", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
