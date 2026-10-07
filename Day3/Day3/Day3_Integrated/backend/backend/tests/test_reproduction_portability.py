from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_MANIFEST = ROOT.parent / "data" / "deng_day3_data_manifest.json"
SCRIPT = ROOT / "scripts" / "reproduce_deng_day3_data.py"


def _script_module():
    spec = importlib.util.spec_from_file_location("deng_reproduction_script", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_json_writer_is_utf8_without_bom_and_lf_only(tmp_path):
    out = tmp_path / "result.json"
    _script_module().write_json(out, {'\u4e2d\u6587': '\u5f00\u53d1', "line": "A\nB"})
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
    assert '\u4e2d\u6587' in raw.decode("utf-8")


def test_reproduction_in_space_named_output_has_byte_identical_delivered_data(tmp_path):
    out = tmp_path / "Windows style output with spaces"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), "--expected-manifest", str(DATA_MANIFEST)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "REPRODUCTION_PASS" in completed.stdout
    for name in (
        "deng_day3_monte_carlo_full_UNAPPROVED.json",
        "deng_day3_matrix_deltas_UNAPPROVED.json",
        "deng_day3_formula_traces_UNAPPROVED.json",
    ):
        raw = (out / name).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw and raw.endswith(b"\n")
