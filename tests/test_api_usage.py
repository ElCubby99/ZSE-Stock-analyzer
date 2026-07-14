"""M19-A: trošak API poziva — determinističke provjere bez baze/mreže."""
from src import api_usage


def test_opus_extraction_cost():
    # 100k in, 8k out na Opus 4.8: (100k*5 + 8k*25)/1e6 = 0.70 USD -> * usd_eur
    p = api_usage.pricing()
    c = api_usage.estimate_cost_eur("claude-opus-4-8", 100_000, 8_000)
    assert abs(c - 0.70 * p["usd_eur"]) < 1e-9


def test_haiku_dated_id_prefix_match():
    c = api_usage.estimate_cost_eur("claude-haiku-4-5-20251001", 500, 100)
    p = api_usage.pricing()
    assert abs(c - (500 * 1 + 100 * 5) / 1e6 * p["usd_eur"]) < 1e-12


def test_batch_half_price():
    full = api_usage.estimate_cost_eur("claude-opus-4-8", 100_000, 8_000)
    half = api_usage.estimate_cost_eur("claude-opus-4-8", 100_000, 8_000, batch=True)
    assert abs(half - full / 2) < 1e-12


def test_cache_multipliers():
    p = api_usage.pricing()
    c = api_usage.estimate_cost_eur(
        "claude-opus-4-8", 0, 0,
        cache_creation_input_tokens=10_000, cache_read_input_tokens=100_000)
    expected = (10_000 * 5 / 1e6 * p["cache_write_multiplier"]
                + 100_000 * 5 / 1e6 * p["cache_read_multiplier"]) * p["usd_eur"]
    assert abs(c - expected) < 1e-12


def test_unknown_model_returns_none():
    assert api_usage.estimate_cost_eur("gpt-x", 1000, 100) is None


def test_budget_env_override(monkeypatch):
    monkeypatch.setenv("API_BUDGET_EUR", "123.5")
    assert api_usage.monthly_budget_eur() == 123.5
    monkeypatch.delenv("API_BUDGET_EUR")
    assert api_usage.monthly_budget_eur() == api_usage.pricing()["monthly_budget_eur"]
