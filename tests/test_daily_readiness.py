"""M32: readiness/retry za EOD cijene — uspjeh vraća broj zapisa, istek
deadlinea bez podataka vraća timeout flag i NIŠTA ne prepisuje; exit kod
runa je 3 samo kad readiness istekne bez ikakvih novih podataka."""
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config, daily  # noqa: E402


@pytest.fixture()
def conn():
    c = psycopg2.connect(config.dsn())
    c.autocommit = False
    yield c
    c.rollback()
    c.close()


def _quiet_log(*_a, **_k):
    pass


def test_uspjeh_vraca_broj_zapisa(conn, monkeypatch):
    from src import prices
    monkeypatch.setattr(prices, "fetch_zse_json", lambda tickers, dates: 42)
    n, timeout = daily.stage_prices(conn, "test-run", _quiet_log)
    assert (n, timeout) == (42, False)


def test_istek_deadlinea_bez_podataka(conn, monkeypatch):
    """Feed uporno prazan + deadline u prošlosti -> odmah timeout, bez
    spavanja (nema retryja nakon isteka) i bez iznimke."""
    from src import prices
    calls = {"n": 0}

    def empty_feed(tickers, dates):
        calls["n"] += 1
        return 0
    monkeypatch.setattr(prices, "fetch_zse_json", empty_feed)
    monkeypatch.setenv("EOD_RETRY_DEADLINE", "00:00")  # uvijek u prošlosti
    n, timeout = daily.stage_prices(conn, "test-run", _quiet_log)
    assert (n, timeout) == (0, True)
    assert calls["n"] == 1, "nakon isteklog deadlinea nema daljnjih pokušaja"


def test_retry_pa_uspjeh(conn, monkeypatch):
    """Prvi pokušaj prazan, drugi vraća podatke — retry petlja radi."""
    from src import daily as d
    from src import prices
    seq = iter([0, 17])
    monkeypatch.setattr(prices, "fetch_zse_json", lambda t, dd: next(seq))
    monkeypatch.setenv("EOD_RETRY_DEADLINE", "23:59")
    monkeypatch.setenv("EOD_RETRY_INTERVAL_MIN", "1")
    slept = []
    import time
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    n, timeout = d.stage_prices(conn, "test-run", _quiet_log)
    assert (n, timeout) == (17, False)
    assert slept == [60], "između pokušaja se čeka interval"


def test_greska_feeda_ne_rusi_stage(conn, monkeypatch):
    from src import prices

    def boom(t, dd):
        raise RuntimeError("mreža pukla")
    monkeypatch.setattr(prices, "fetch_zse_json", boom)
    monkeypatch.setenv("EOD_RETRY_DEADLINE", "00:00")
    n, timeout = daily.stage_prices(conn, "test-run", _quiet_log)
    assert (n, timeout) == (0, True)
