"""Regression tests for cross-platform Monte Carlo benchmark telemetry."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark_monte_carlo.py"


def _load_benchmark_module():
    spec = importlib.util.spec_from_file_location("causora_benchmark_monte_carlo", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_peak_rss_is_explicitly_unavailable_without_posix_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows lacks resource; elapsed-time benchmarking must still be usable."""
    benchmark = _load_benchmark_module()
    monkeypatch.setattr(benchmark, "resource", None)

    peak_rss_mib, status, source = benchmark._peak_rss_measurement()

    assert peak_rss_mib is None
    assert status == "unavailable"
    assert source == "resource module is unavailable on this platform"


def test_peak_rss_failure_is_not_silently_replaced_with_a_number(monkeypatch: pytest.MonkeyPatch) -> None:
    benchmark = _load_benchmark_module()

    class BrokenResource:
        RUSAGE_SELF = object()

        @staticmethod
        def getrusage(_target):
            raise OSError("RSS unavailable")

    monkeypatch.setattr(benchmark, "resource", BrokenResource())
    peak_rss_mib, status, source = benchmark._peak_rss_measurement()

    assert peak_rss_mib is None
    assert status == "unavailable"
    assert source == "resource.getrusage could not provide peak RSS"
