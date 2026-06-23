"""Čisti unit testovi za normalizaciju i derivacije (bez baze, bez API-ja)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.normalize import derive_items, to_eur  # noqa: E402


def test_scale_thousands():
    assert to_eur(1234, 1000, "EUR") == 1234000


def test_scale_millions():
    assert to_eur(2, 1_000_000, "EUR") == 2_000_000


def test_hrk_conversion():
    # 7534.50 HRK / 7.53450 = 1000 EUR
    assert abs(to_eur(7534.50, 1, "HRK") - 1000.0) < 1e-6


def test_none_passthrough():
    assert to_eur(None, 1000, "EUR") is None


def test_derive_ebitda_when_missing():
    d = derive_items({"ebit": 100.0, "depreciation_amortization": 30.0})
    assert d["ebitda"] == 130.0


def test_derive_ebitda_skipped_when_reported():
    d = derive_items({"ebitda": 999.0, "ebit": 100.0, "depreciation_amortization": 30.0})
    assert "ebitda" not in d


def test_derive_net_debt():
    d = derive_items({"debt_short": 50.0, "debt_long": 150.0, "cash_and_equivalents": 80.0})
    assert d["total_debt"] == 200.0
    assert d["net_debt"] == 120.0


def test_derive_fcf():
    d = derive_items({"operating_cf": 300.0, "capex": 120.0})
    assert d["free_cash_flow"] == 180.0


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
