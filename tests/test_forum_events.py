"""M77: AI Forum živi — event-komentari + odgovori na @spomene.

Lokalna dev baza NEMA Supabase forum tablice (žive u produkciji kroz
migration_discussions.sql), pa testovi unutar transakcije s ROLLBACK-om
kreiraju POJEDNOSTAVLJENE tablice istih stupaca (bez auth.users FK) —
provjerava se SQL logika i tok, ne RLS. API pozivi su lažni (injektirani
`generate`), nikad pravi. Preskaču se bez lokalne baze.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import forum_events  # noqa: E402


def _connect():
    try:
        import psycopg2

        from src import config
        c = psycopg2.connect(config.dsn())
        with c.cursor() as cur:
            cur.execute("SELECT 1")
        return c
    except Exception:  # noqa: BLE001
        return None


class _NoCommit:
    """Omotač: funkcije modula zovu conn.commit() nakon svakog posta — u
    testu commit mora biti no-op da ROLLBACK počisti i DDL i podatke."""

    def __init__(self, conn):
        self._c = conn

    def cursor(self):
        return self._c.cursor()

    def commit(self):
        pass

    def rollback(self):
        self._c.rollback()


DDL = """
CREATE TABLE IF NOT EXISTS ai_agents (
  id text PRIMARY KEY, display_name_hr text, display_name_en text,
  role_prompt text, model text, is_active boolean DEFAULT true);
CREATE TABLE IF NOT EXISTS discussions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker text, round_no int, trigger text DEFAULT 'manual',
  status text DEFAULT 'draft', kind text DEFAULT 'ai_round',
  slug text, title_hr text, title_en text, related_href text,
  related_href_en text, data_snapshot jsonb, summary_hr text,
  summary_en text, agree_points jsonb, disagree_points jsonb,
  questions_for_humans jsonb, published_at timestamptz,
  created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS discussion_posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  discussion_id uuid, author_type text, agent_id text, user_id uuid,
  volley_no int, reply_to uuid, body_hr text, body_en text,
  citations jsonb DEFAULT '[]'::jsonb, status text DEFAULT 'published',
  model_used text, tokens_in int, tokens_out int, cost_usd numeric,
  ip_hash text, created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS agent_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  discussion_id uuid, agent_id text, ticker text, stance text,
  horizon_months int, price_at_call numeric, zone_low numeric,
  zone_high numeric, invalidation_condition text,
  created_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS agent_summons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  discussion_id uuid, post_id uuid, agent_id text, user_id uuid,
  status text DEFAULT 'queued', reply_post_id uuid,
  created_at timestamptz DEFAULT now(), processed_at timestamptz);
CREATE TABLE IF NOT EXISTS usage_limits (
  key text PRIMARY KEY, value_int int, note text);
CREATE TABLE IF NOT EXISTS user_flags (
  user_id uuid PRIMARY KEY, can_comment boolean DEFAULT true,
  can_summon boolean DEFAULT true, is_banned boolean DEFAULT false,
  note text);
"""


@pytest.fixture()
def conn():
    c = _connect()
    if c is None:
        pytest.skip("lokalna baza nedostupna")
    with c.cursor() as cur:
        cur.execute(DDL)
        cur.execute("""INSERT INTO ai_agents (id, display_name_hr,
                         display_name_en, role_prompt, model) VALUES
                       ('ai_value','Vrijednosni','Value','test prompt','m'),
                       ('ai_owner','Vlasnički','Ownership','test prompt','m')
                       ON CONFLICT (id) DO NOTHING""")
        cur.execute("""INSERT INTO usage_limits (key, value_int) VALUES
                       ('global_cost_cap_usd_day', 5),
                       ('summons_per_user_day', 1),
                       ('summons_per_user_week', 5),
                       ('summons_per_thread_day', 5),
                       ('global_summons_per_day', 50)
                       ON CONFLICT (key) DO NOTHING""")
    yield _NoCommit(c)
    c.rollback()
    c.close()


def _fake_generate(agent, prompt, *, ticker, conn, operation):
    return {
        "body_hr": "Testni komentar s izvorom.",
        "body_en": "Test comment with a source.",
        "citations": [{"label": "EHO objava",
                       "source_url": "test://forum-event"}],
        "model": "test-model", "tokens_in": 10, "tokens_out": 20,
        "cost_usd": 0.001,
    }


def _mk_thread(cur, ticker="HPB"):
    cur.execute("""INSERT INTO discussions (ticker, round_no, status, kind,
                     data_snapshot, published_at)
                   VALUES (%s, 99, 'published', 'ai_round', '{}'::jsonb,
                           now()) RETURNING id""", (ticker,))
    return cur.fetchone()[0]


def _cid(cur, ticker="HPB"):
    cur.execute("SELECT id FROM companies WHERE ticker=%s", (ticker,))
    return cur.fetchone()[0]


def test_event_komentar_dividenda_i_dedupe(conn):
    """Svježa dividenda za nit s objavljenom rundom -> Vlasnički komentira
    (volley_no NULL, citat izvora); drugi run je no-op (dedupe po izvoru)."""
    with conn.cursor() as cur:
        disc = _mk_thread(cur)
        cur.execute(
            """INSERT INTO dividends (company_id, class_ticker, fiscal_year,
                 amount_eur, div_type, ex_date, source_url)
               VALUES (%s, 'HPB', EXTRACT(YEAR FROM CURRENT_DATE)::int - 1,
                       9.99, 'Izglasana dividenda', CURRENT_DATE + 10,
                       'test://forum-event')""", (_cid(cur),))
    n = forum_events.post_event_comments(conn, lambda m: None,
                                         generate=_fake_generate)
    assert n == 1
    with conn.cursor() as cur:
        cur.execute("""SELECT agent_id, volley_no, status, citations
                       FROM discussion_posts WHERE discussion_id=%s""", (disc,))
        rows = cur.fetchall()
    assert len(rows) == 1
    agent_id, volley, status, cits = rows[0]
    assert agent_id == "ai_owner" and volley is None and status == "published"
    assert cits[0]["source_url"] == "test://forum-event"
    # idempotentnost preko runova
    n2 = forum_events.post_event_comments(conn, lambda m: None,
                                          generate=_fake_generate)
    assert n2 == 0


def test_event_gate_stari_ex_datum(conn):
    """Backfill zapis (davno prošli ex-datum) NIJE događaj — M66 gate."""
    with conn.cursor() as cur:
        _mk_thread(cur)
        cur.execute(
            """INSERT INTO dividends (company_id, class_ticker, fiscal_year,
                 amount_eur, div_type, ex_date, source_url)
               VALUES (%s, 'HPB', EXTRACT(YEAR FROM CURRENT_DATE)::int - 1,
                       1.11, 'Izglasana dividenda', CURRENT_DATE - 400,
                       'test://forum-old')""", (_cid(cur),))
        assert forum_events.collect_events(cur) == []


def test_summons_odgovor_samo_na_odobren_komentar(conn):
    """Spomen na odobrenom (published) komentaru dobiva odgovor u niti;
    spomen na pending komentaru ostaje queued (čeka moderatora)."""
    with conn.cursor() as cur:
        disc = _mk_thread(cur)
        cur.execute("""INSERT INTO discussion_posts (discussion_id,
                         author_type, user_id, body_hr, status)
                       VALUES (%s, 'human', gen_random_uuid(),
                               'Pitanje za @ai_value?', 'published'),
                              (%s, 'human', gen_random_uuid(),
                               'Drugo pitanje', 'pending')
                       RETURNING id, user_id""", (disc, disc))
        (p_pub, u_pub), (p_pend, u_pend) = cur.fetchall()
        cur.execute("""INSERT INTO agent_summons (discussion_id, post_id,
                         agent_id, user_id) VALUES (%s,%s,'ai_value',%s),
                                                   (%s,%s,'ai_value',%s)""",
                    (disc, p_pub, u_pub, disc, p_pend, u_pend))
    n = forum_events.answer_summons(conn, lambda m: None,
                                    generate=_fake_generate)
    assert n == 1
    with conn.cursor() as cur:
        cur.execute("""SELECT post_id, status, reply_post_id
                       FROM agent_summons WHERE discussion_id=%s""", (disc,))
        by_post = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        assert by_post[p_pub][0] == "answered" and by_post[p_pub][1]
        assert by_post[p_pend][0] == "queued"  # čeka odobrenje
        cur.execute("""SELECT agent_id, reply_to, volley_no
                       FROM discussion_posts
                       WHERE discussion_id=%s AND author_type='ai'""", (disc,))
        agent_id, reply_to, volley = cur.fetchone()
        assert agent_id == "ai_value" and reply_to == p_pub and volley is None


def test_summons_filter_pad_znaci_rejected(conn):
    """Generacija koja padne (MAR/format) NE objavljuje ništa — spomen
    završava kao rejected_filter."""
    with conn.cursor() as cur:
        disc = _mk_thread(cur)
        cur.execute("""INSERT INTO discussion_posts (discussion_id,
                         author_type, user_id, body_hr, status)
                       VALUES (%s, 'human', gen_random_uuid(), 'P?',
                               'published') RETURNING id, user_id""", (disc,))
        p_id, u_id = cur.fetchone()
        cur.execute("""INSERT INTO agent_summons (discussion_id, post_id,
                         agent_id, user_id)
                       VALUES (%s,%s,'ai_value',%s)""", (disc, p_id, u_id))
    n = forum_events.answer_summons(
        conn, lambda m: None,
        generate=lambda *a, **k: None)
    assert n == 0
    with conn.cursor() as cur:
        cur.execute("""SELECT status FROM agent_summons
                       WHERE discussion_id=%s""", (disc,))
        assert cur.fetchone()[0] == "rejected_filter"
        cur.execute("""SELECT count(*) FROM discussion_posts
                       WHERE discussion_id=%s AND author_type='ai'""", (disc,))
        assert cur.fetchone()[0] == 0


def test_reseed_cuva_zive_postove(conn):
    """M77: reseed runde (load_discussions) briše protokolarne postove
    (volley_no postavljen), ali NE event-komentare i odgovore na spomene
    (volley_no NULL)."""
    from scripts.load_discussions import load_file
    doc = {
        "discussion": {"ticker": "TSTF", "round_no": 99,
                       "data_snapshot": {"as_of": "2026-08-25"}},
        "posts": [{"agent_id": "ai_value", "volley_no": 0,
                   "body_hr": "Uvodni post.",
                   "citations": [{"label": "test"}]}],
    }
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
        path = f.name
    with conn.cursor() as cur:
        load_file(cur, path)
        cur.execute("SELECT id FROM discussions WHERE ticker='TSTF'")
        disc = cur.fetchone()[0]
        # "živi" post (event-komentar): volley_no NULL
        cur.execute("""INSERT INTO discussion_posts (discussion_id,
                         author_type, agent_id, volley_no, body_hr, citations)
                       VALUES (%s, 'ai', 'ai_owner', NULL, 'Event komentar.',
                               '[{"label":"x"}]'::jsonb)""", (disc,))
        load_file(cur, path)  # reseed
        cur.execute("""SELECT volley_no, body_hr FROM discussion_posts
                       WHERE discussion_id=%s AND author_type='ai'
                       ORDER BY volley_no NULLS LAST""", (disc,))
        rows = cur.fetchall()
    assert (0, "Uvodni post.") in rows, "protokolarni post nije reseedan"
    assert (None, "Event komentar.") in rows, "živi post NE smije nestati"
