"""v3 FAZA SOTP (točka 4): topološki redoslijed preračuna zona.

Pipeline računa zone po grafu ovisnosti iz v_sotp_inputs: prvo firme bez
SOTP ovisnosti (kćeri), zatim matice — NIKAD stara zona kćeri u novom
SOTP-u matice. Ciklus u grafu = greška koja se PRIJAVLJUJE (CycleError),
ne tiho ignorira.

Napomena: rekurzivni SOTP (fair_equity_of) ionako računa kćer svježe u
letu; topološki red dodatno jamči da su i SNAPSHOTOVI (valuations,
per-stock JSON exporti) pisani u ispravnom redoslijedu i da se ciklus u
podacima ne može provući neopaženo.
"""
from __future__ import annotations


class CycleError(RuntimeError):
    """Ciklus u SOTP grafu ovisnosti — podatkovna greška, ne stanje."""


def dependency_graph(conn) -> dict[str, set[str]]:
    """ticker matice -> skup tickera kćeri (samo praćene firme)."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.ticker, h.ticker
               FROM v_sotp_inputs v
               JOIN companies p ON p.id = v.parent_company_id
               LEFT JOIN companies h ON h.id = v.held_company_id
               WHERE v.held_company_id IS NOT NULL""")
        g: dict[str, set[str]] = {}
        for parent, held in cur.fetchall():
            if held:
                g.setdefault(parent, set()).add(held)
    return g


def topo_order(tickers: list[str], graph: dict[str, set[str]]) -> list[str]:
    """Kahn: kćeri prije matica. Tickeri izvan grafa zadržavaju abecedni
    red među sobom. Ciklus -> CycleError s imenima u ciklusu."""
    tickers = list(tickers)
    tset = set(tickers)
    deps = {t: {d for d in graph.get(t, ()) if d in tset} for t in tickers}
    out: list[str] = []
    ready = sorted(t for t in tickers if not deps[t])
    remaining = {t for t in tickers if deps[t]}
    done: set[str] = set()
    while ready:
        t = ready.pop(0)
        out.append(t)
        done.add(t)
        newly = sorted(r for r in remaining if deps[r] <= done)
        for r in newly:
            remaining.discard(r)
        ready.extend(newly)
    if remaining:
        raise CycleError(
            "ciklus u SOTP grafu ovisnosti (matica<->kći): "
            + ", ".join(sorted(remaining))
            + " — provjeri v_sotp_inputs/holdings; preračun ZAUSTAVLJEN "
            "(radije greška nego stara zona kćeri u SOTP-u matice)")
    return out


def ordered_tickers(conn, tickers: list[str]) -> list[str]:
    return topo_order(tickers, dependency_graph(conn))
