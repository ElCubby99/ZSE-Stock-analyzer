"""Postgres konekcija."""
from __future__ import annotations

from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from . import config


@contextmanager
def get_conn():
    """Yield-a konekciju; commit na izlazu, rollback na grešci."""
    conn = psycopg2.connect(config.dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
