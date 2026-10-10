from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("day5_local_launcher", ROOT / "scripts/start_day5.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def test_simulation_launcher_strips_keys_authorization_and_preserves_parent(monkeypatch):
    values = {
        "OPENAI_API_KEY": "NOT_A_REAL_KEY_TEST_FIXTURE_ONLY",
        "OPENAI_API_BASE": "https://unused.invalid",
        "OPENROUTER_API_KEY": "NOT_A_REAL_KEY_TEST_FIXTURE_ONLY",
        "CAUSORA_OPENROUTER_BUDGET_JOURNAL": "/existing/persistent/journal.json",
        "CAUSORA_OPENROUTER_PAID_AUTHORIZATION": "fixture",
        "CAUSORA_DEV_UNREVIEWED_MODE": "UNREVIEWED_DEV_ONLY",
        "CAUSORA_DAY4_UNREVIEWED_PROVIDER_DEVELOPMENT_ONLY": "fixture",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    env = launcher.simulation_environment()
    for key in values:
        assert key not in env
        assert os.environ[key] == values[key]
    assert env["CAUSORA_AI_PROVIDER"] == "openrouter"


def test_launcher_does_not_touch_or_initialize_budget_journal(monkeypatch, tmp_path):
    journal = tmp_path / "journal.json"
    original = b'{"fixture":"TEST_FIXTURE_ONLY","used":6}\n'
    journal.write_bytes(original)
    monkeypatch.setenv("CAUSORA_OPENROUTER_BUDGET_JOURNAL", str(journal))
    launcher.simulation_environment()
    assert journal.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["journal.json"]


def test_launcher_refuses_occupied_port_without_stopping_listener():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        with pytest.raises(RuntimeError, match="occupied"):
            launcher.ensure_port_free(port)
        assert listener.fileno() >= 0


def test_windows_entries_resolve_existing_scripts():
    for name in ("setup-windows.ps1", "start-day5.ps1", "start_day5.py"):
        assert (ROOT / "scripts" / name).is_file()
