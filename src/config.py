"""Konfiguracija: env varijable, DB DSN, model, tečaj."""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv nije obavezan u runtimeu
    pass


PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
ZSE_DB = os.getenv("ZSE_DB", "zse")
ZSE_USER = os.getenv("ZSE_USER", "zse")
ZSE_PASS = os.getenv("ZSE_PASS", "zse")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

# Fiksni tečaj HRK->EUR (konverzija HRK iznosa do 2022).
HRK_EUR_RATE = float(os.getenv("HRK_EUR_RATE", "7.53450"))


def dsn() -> str:
    return (
        f"host={PGHOST} port={PGPORT} dbname={ZSE_DB} "
        f"user={ZSE_USER} password={ZSE_PASS}"
    )
