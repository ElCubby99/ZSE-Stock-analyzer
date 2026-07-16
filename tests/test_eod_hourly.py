"""M34: satni EOD pokušaji — simulacije iz acceptance kriterija.

1. izvor bez podataka -> neutralan izlaz (not_ready), bez iznimke, bez regena
2. izvor s podacima -> povlačenje; nakon upisa je eod_already_done True pa
   su svi kasniji runovi tog dana no-op ("already done")
3. zadnji dnevni pokušaj bez podataka -> exit 3 (jedan alarm); raniji ne
4. backfill: rupa za jučer + izvor nudi oba datuma -> oba povučena u runu
5. nijedan run ne sadrži sleep/wait petlju > 60 s (grep koda i workflowa)
6. DST guard i concurrency rade s novim rasporedom (provjera workflow YAML-a)
"""
import pathlib
import sys
from datetime import date, datetime

import psycopg2
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import config, daily  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def conn():
    c = psycopg2.connect(config.dsn())
    c.autocommit = False
    yield c
    c.rollback()
    c.close()


def _quiet_log(*_a, **_k):
    pass


# ---------- 1. izvor bez podataka -> neutralno ----------

def test_bez_podataka_neutralan_izlaz(conn):
    calls = []

    def empty_feed(tickers, dates):
        calls.append(list(dates))
        return 0
    n, not_ready = daily.stage_prices(conn, "test-run", _quiet_log, fetch=empty_feed)
    assert (n, not_ready) == (0, True)
    assert len(calls) == 1, "jedan kratki pokušaj — čekanje rade cronovi, ne runner"


def test_greska_feeda_ne_rusi_stage(conn):
    def boom(t, dd):
        raise RuntimeError("mreža pukla")
    n, not_ready = daily.stage_prices(conn, "test-run", _quiet_log, fetch=boom)
    assert (n, not_ready) == (0, True)


# ---------- 2. podaci dostupni -> povlačenje; kasniji runovi no-op ----------

def test_uspjeh_pa_already_done(conn):
    """Fake feed 'upiše' današnje cijene (kao pravi fetch, u prices_eod);
    nakon toga idempotentni guard kaže done -> satna serija je sigurna."""
    today = date.today()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT sc.company_id, sc.id FROM share_classes sc
               JOIN companies c ON c.id=sc.company_id WHERE c.is_live""")
        classes = cur.fetchall()
    assert classes, "test traži live klase u bazi"

    def feed_writes(tickers, dates):
        n = 0
        with conn.cursor() as cur:
            for cid, scid in classes:
                cur.execute(
                    """INSERT INTO prices_eod (company_id, share_class_id,
                         trade_date, close_eur, source)
                       VALUES (%s,%s,%s, 1.0, 'test')
                       ON CONFLICT (company_id, trade_date,
                                    COALESCE(share_class_id, 0))
                       DO NOTHING""", (cid, scid, dates[0]))
                n += 1
        return n

    assert not daily.eod_already_done(conn, today), "test kreće iz praznog dana"
    n, not_ready = daily.stage_prices(conn, "test-run", _quiet_log, fetch=feed_writes)
    assert n > 0 and not not_ready
    assert daily.eod_already_done(conn, today), \
        "nakon uspjeha guard mora vratiti done (sljedeći runovi = no-op)"


def test_prag_kompletnosti(conn):
    """Djelomičan upis ispod praga NIJE done (kriterij: udio klasa >= prag)."""
    today = date.today()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT sc.company_id, sc.id FROM share_classes sc
               JOIN companies c ON c.id=sc.company_id WHERE c.is_live LIMIT 3""")
        few = cur.fetchall()
        for cid, scid in few:
            cur.execute(
                """INSERT INTO prices_eod (company_id, share_class_id, trade_date,
                     close_eur, source) VALUES (%s,%s,%s,1.0,'test')
                   ON CONFLICT (company_id, trade_date, COALESCE(share_class_id,0))
                   DO NOTHING""", (cid, scid, today))
    assert not daily.eod_already_done(conn, today), \
        "3 klase od ~69 ne smije proći kao kompletan dan"


def test_exports_fresh_iz_overviewa(tmp_path):
    """Guard 'already done' traži i svježe exporte: baza s cijenama ali
    stari overview.json (run pao prije regena, slučaj 16.07.) NE smije
    proći kao done — sljedeći run mora nadoknaditi regen + deploy."""
    import json as _json
    p = tmp_path / "overview.json"
    today = date.today()

    p.write_text(_json.dumps({"stocks": [{"date": today.isoformat()}]}))
    assert daily.exports_fresh(overview_path=p) is True

    p.write_text(_json.dumps({"stocks": [{"date": "2020-01-02"}]}))
    assert daily.exports_fresh(overview_path=p) is False, \
        "stari exporti uz punu bazu = nadoknada, ne no-op"

    p.write_text("{pokvaren json")
    assert daily.exports_fresh(overview_path=p) is False
    assert daily.exports_fresh(overview_path=tmp_path / "nema.json") is False


# ---------- 3. alarm samo na zadnjem dnevnom pokušaju ----------

def test_final_attempt_prag(monkeypatch):
    class FakeNow:
        def __init__(self, h):
            self.hour = h
    for h, final in [(16, False), (18, False), (21, False), (22, True), (23, True)]:
        monkeypatch.setattr(daily, "_zagreb_now", lambda h=h: FakeNow(h))
        assert daily._is_final_attempt() == final, f"sat {h}"


def test_attempt_numbering(monkeypatch):
    class FakeNow:
        def __init__(self, h):
            self.hour = h
    for h, expected in [(16, 1), (19, 4), (22, 7), (23, 7), (15, 1)]:
        monkeypatch.setattr(daily, "_zagreb_now", lambda h=h: FakeNow(h))
        n, m = daily._attempt_no()
        assert (n, m) == (expected, 7), f"sat {h}"


# ---------- 4. backfill jučerašnje rupe ----------

def test_backfill_jucerasnje_rupe(conn):
    today = date.today()
    prev = daily.previous_trading_day(today)
    # simuliraj rupu: obriši jučerašnje zapise (u transakciji — rollback poslije)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM prices_eod WHERE trade_date=%s", (prev,))
    assert not daily.eod_already_done(conn, prev)

    fetched_dates = []

    def feed_both(tickers, dates):
        fetched_dates.extend(dates)
        # upiši zapise za traženi datum u ISTOJ transakciji (test okvir)
        with conn.cursor() as cur:
            cur.execute(
                """SELECT sc.company_id, sc.id FROM share_classes sc
                   JOIN companies c ON c.id=sc.company_id WHERE c.is_live""")
            for cid, scid in cur.fetchall():
                cur.execute(
                    """INSERT INTO prices_eod (company_id, share_class_id,
                         trade_date, close_eur, source)
                       VALUES (%s,%s,%s,1.0,'test')
                       ON CONFLICT (company_id, trade_date,
                                    COALESCE(share_class_id,0)) DO NOTHING""",
                    (cid, scid, dates[0]))
        return 60

    n, not_ready = daily.stage_prices(conn, "test-run", _quiet_log, fetch=feed_both)
    assert n > 0 and not not_ready
    assert today.isoformat() in fetched_dates and prev.isoformat() in fetched_dates, \
        f"oba datuma moraju biti povučena u istom runu: {fetched_dates}"
    assert daily.eod_already_done(conn, prev), "serija ne smije ostati s rupom"


def test_previous_trading_day_preskace_vikend():
    assert daily.previous_trading_day(date(2026, 7, 20)) == date(2026, 7, 17)  # pon -> pet
    assert daily.previous_trading_day(date(2026, 7, 16)) == date(2026, 7, 15)  # čet -> sri


# ---------- 5. bez sleep/wait petlji > 60 s ----------

def test_nema_sleep_petlje():
    src = (ROOT / "src" / "daily.py").read_text(encoding="utf-8")
    assert "sleep(" not in src, "daily.py ne smije spavati — čekanje rade cronovi"
    wf = (ROOT / ".github" / "workflows" / "daily-eod.yml").read_text(encoding="utf-8")
    import re
    for m in re.finditer(r"sleep\s+\$\(\((.*?)\)\)|sleep\s+(\d+)", wf):
        if m.group(2):
            assert int(m.group(2)) <= 60, f"sleep > 60 s u workflowu: {m.group(0)}"
        else:
            assert "2**i" in m.group(1), f"nepoznata sleep formula: {m.group(0)}"
            # 2**i za i<=4 -> max 16 s (git push retry) — dopušteno


# ---------- 6. raspored, guard i concurrency u workflow YAML-u ----------

def test_workflow_raspored_i_guard():
    wf = (ROOT / ".github" / "workflows" / "daily-eod.yml").read_text(encoding="utf-8")
    assert "'20 14-20 * * 1-5'" in wf, "satni CEST raspon 16:20-22:20"
    assert "'20 15-21 * * 1-5'" in wf, "satni CET raspon 16:20-22:20"
    assert '-ge 16' in wf and '-le 22' in wf, "guard prozor 16-23h lokalno"
    assert "workflow_dispatch" in wf, "ručna nadoknada mora ostati"
    assert "group: daily-eod" in wf and "cancel-in-progress: false" in wf, \
        "concurrency bez paralelnih runova"
    assert "did_work" in wf, "no-op runovi moraju preskočiti commit/deploy korake"
    assert "not yet published" in wf, "SUCCESS s 'not yet' logom je normalan ishod"
