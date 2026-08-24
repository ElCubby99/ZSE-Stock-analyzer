"""NALOG M30: logika @spomena — ČISTE funkcije bez baze i bez API poziva.

Edge Function discussion-comment puni red (agent_summons); obrada reda
(scripts/discussions_run.py, SUMMONS_ENABLED=false) koristi ove funkcije za
odluku smije li spomen dobiti odgovor. Redoslijed provjera je ugovor iz
naloga: can_summon -> per_user_day -> per_user_week -> per_thread_day ->
global_per_day -> global_cost_cap. PRVI pad odlučuje status.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MENTION_RX = re.compile(r"@(ai_[a-z]+)\b")

# moderator se ne poziva; spomeni iz AI postova se ignoriraju po konstrukciji
NON_SUMMONABLE = {"ai_mod"}


def parse_mentions(body: str, author_type: str = "human") -> list[str]:
    """Jedinstveni spomeni agenata iz LJUDSKOG posta, redoslijedom pojave.
    AI post -> uvijek prazno (nema lančane reakcije)."""
    if author_type != "human":
        return []
    seen, out = set(), []
    for m in MENTION_RX.finditer(body or ""):
        aid = m.group(1)
        if aid not in seen and aid not in NON_SUMMONABLE:
            seen.add(aid)
            out.append(aid)
    return out


@dataclass
class SummonContext:
    """Brojila u trenutku odluke (puni ih orkestrator iz baze)."""
    can_summon: bool = True
    user_summons_today: int = 0
    user_summons_week: int = 0
    thread_summons_today: int = 0
    global_summons_today: int = 0
    global_cost_today_usd: float = 0.0
    limits: dict = field(default_factory=dict)

    def limit(self, key: str, default: int) -> int:
        return int(self.limits.get(key, default))


def decide_summon(ctx: SummonContext) -> tuple[str, str | None]:
    """('queued'|'rejected_limit'|'deferred', razlog) — bez side-effecta.

    'deferred' = korisniku se kaže "agent se javlja u sljedećoj rundi"
    (meki padovi: dnevni/tjedni limiti korisnika). Tvrdi padovi (flag,
    globalni cap) -> 'rejected_limit'."""
    if not ctx.can_summon:
        return "rejected_limit", "can_summon=false"
    if ctx.user_summons_today >= ctx.limit("summons_per_user_day", 1):
        return "deferred", "summons_per_user_day"
    if ctx.user_summons_week >= ctx.limit("summons_per_user_week", 5):
        return "deferred", "summons_per_user_week"
    if ctx.thread_summons_today >= ctx.limit("summons_per_thread_day", 5):
        return "deferred", "summons_per_thread_day"
    if ctx.global_summons_today >= ctx.limit("global_summons_per_day", 50):
        return "rejected_limit", "global_summons_per_day"
    if ctx.global_cost_today_usd >= ctx.limit("global_cost_cap_usd_day", 5):
        return "rejected_limit", "global_cost_cap_usd_day"
    return "queued", None


# MAR filter — isti izrazi kao u Edge Functionima (izvor istine za testove)
FORBIDDEN_RX = [
    re.compile(r"\bkupi(te)?\b", re.I),
    re.compile(r"\bprodaj(te)?\b", re.I),
    re.compile(r"\bpreporu[čc]ujem\b", re.I),
    re.compile(r"\bpreporu[čc]amo\b", re.I),
    re.compile(r"\bciljna cijena\b", re.I),
    re.compile(r"\btarget price\b", re.I),
    re.compile(r"\bstrong (buy|sell)\b", re.I),
    re.compile(r"\b(buy|sell) rating\b", re.I),
]


def forbidden_hit(text: str) -> str | None:
    """Prvi zabranjeni izraz u tekstu ili None. Za AI output: pad znači
    regeneriraj jednom, pa 'rejected_filter'."""
    for rx in FORBIDDEN_RX:
        if rx.search(text or ""):
            return rx.pattern
    return None
