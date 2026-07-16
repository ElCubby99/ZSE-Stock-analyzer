"""v3 FAZA SOTP (acceptance 5c-1): topološki preračun + prijava ciklusa."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.sotp_order import CycleError, topo_order  # noqa: E402


def test_kceri_prije_matica():
    g = {"ADRS": {"CROS", "MAIS"}, "KOEI": {"KODT", "DLKV"}}
    order = topo_order(["ADRS", "CROS", "KODT", "KOEI", "MAIS", "DLKV", "HT"],
                       g)
    assert order.index("CROS") < order.index("ADRS")
    assert order.index("MAIS") < order.index("ADRS")
    assert order.index("KODT") < order.index("KOEI")
    assert order.index("DLKV") < order.index("KOEI")
    assert set(order) == {"ADRS", "CROS", "KODT", "KOEI", "MAIS", "DLKV", "HT"}


def test_umjetni_ciklus_prijavljuje_gresku():
    g = {"A": {"B"}, "B": {"A"}}
    with pytest.raises(CycleError) as e:
        topo_order(["A", "B", "C"], g)
    assert "ciklus" in str(e.value)
    assert "A" in str(e.value) and "B" in str(e.value)


def test_ovisnost_izvan_skupa_se_ignorira():
    # kći koja se ne preračunava (nije u listi) ne smije blokirati maticu
    g = {"KOEI": {"KODT", "NEPOSTOJI"}}
    order = topo_order(["KOEI", "KODT"], g)
    assert order == ["KODT", "KOEI"]
