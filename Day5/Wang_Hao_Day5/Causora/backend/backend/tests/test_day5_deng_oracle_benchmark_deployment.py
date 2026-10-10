from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from evaluation.benchmark.run_offline_benchmark import golden_audit, run as run_benchmark
from evaluation.oracle.independent_oracle import evaluate_document


ORACLE_PATH = PROJECT / "evaluation" / "oracle" / "frozen_control_cases.json"
GOLDEN_PATH = PROJECT / "verification" / "g4-final" / "verified_golden_e2e.json"
ORACLE_IMPLEMENTATION = PROJECT / "evaluation" / "oracle" / "independent_oracle.py"
RENDER_START = PROJECT / "deployment" / "render_start.py"
PREFLIGHT = PROJECT / "deployment" / "deployment_preflight.py"


def _load_render_start():
    spec = importlib.util.spec_from_file_location("day5_render_start", RENDER_START)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_preflight():
    spec = importlib.util.spec_from_file_location("day5_deployment_preflight", PREFLIGHT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_independent_oracle_controls_pass_without_simulation_engine_imports():
    source = ORACLE_IMPLEMENTATION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(name == "app" or name.startswith("simulation_day") for name in imported)
    result = evaluate_document(json.loads(ORACLE_PATH.read_text(encoding="utf-8")))
    assert result["caseCount"] == 6
    assert result["passed"] == 6
    assert result["failed"] == 0


def test_no_cost_benchmark_audits_captured_golden_without_provider_dispatch():
    result = run_benchmark()
    assert result["networkCallsMade"] == 0
    assert result["providerCallsMade"] == 0
    assert result["oracleTechnicalCheck"]["failed"] == 0
    assert result["causora"]["score"]["correctnessStatus"] == "COMPLETED_AND_FULLY_CORRECT"
    assert result["causora"]["score"]["answerAccuracy"]["correctCaseCount"] == 6
    assert result["historicGoldenAudit"]["auditedCells"] == 9
    assert result["plainLlm"]["captureStatus"] == "NOT_RUN_NO_PAID_AUTHORIZATION"
    assert result["llmPlusCode"]["captureStatus"] == "NOT_RUN_NO_PAID_AUTHORIZATION"
    assert result["overallStatus"] == "PARTIAL_CAUSORA_SCORED_PENDING_EXPLICIT_PAID_LLM_AUTHORIZATION"


def test_golden_audit_rejects_trace_component_tampering():
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    golden["simulationResponse"]["data"]["traces"]["baseline"]["D1"]["components"][0]["valueUsd"] += 1
    with pytest.raises(ValueError, match="Golden component mismatch"):
        golden_audit(golden)


def test_render_entry_requires_public_host_and_rejects_development_overrides():
    launcher = _load_render_start()
    assert launcher.production_address({"HOST": "0.0.0.0", "PORT": "8000"}) == ("0.0.0.0", 8000)
    implicit_mode = {}
    launcher.enforce_openrouter_mode(implicit_mode)
    assert implicit_mode["CAUSORA_AI_PROVIDER"] == "openrouter"
    with pytest.raises(ValueError, match="CAUSORA_AI_PROVIDER"):
        launcher.enforce_openrouter_mode({"CAUSORA_AI_PROVIDER": "legacy"})
    with pytest.raises(ValueError, match="CAUSORA_DEV_UNREVIEWED_MODE"):
        launcher.production_address({"HOST": "0.0.0.0", "PORT": "8000", "CAUSORA_DEV_UNREVIEWED_MODE": "UNREVIEWED_DEV_ONLY"})
    with pytest.raises(ValueError, match="CAUSORA_DAY4_UNREVIEWED_PROVIDER_DEVELOPMENT_ONLY"):
        launcher.production_address({"HOST": "0.0.0.0", "PORT": "8000", "CAUSORA_DAY4_UNREVIEWED_PROVIDER_DEVELOPMENT_ONLY": "YES"})
    with pytest.raises(ValueError, match="HOST"):
        launcher.production_address({"HOST": "127.0.0.1", "PORT": "8000"})


def test_deployment_templates_keep_secrets_out_of_source_and_live_build_selected():
    render = (PROJECT / "render.yaml").read_text(encoding="utf-8")
    vercel = json.loads((PROJECT / "frontend" / "vercel.json").read_text(encoding="utf-8"))
    assert "OPENROUTER_API_KEY" not in render
    assert "CAUSORA_DEV_UNREVIEWED_MODE" not in render
    assert "plan: free" in render
    assert "mountPath:" not in render
    assert "sizeGB:" not in render
    assert vercel["buildCommand"] == "npm run build:live"
    assert vercel["outputDirectory"] == "builds/live"


def test_deployment_preflight_ignores_generated_hash_inventory_but_scans_source(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    for relative in ("render.yaml", "deployment/render_start.py", "frontend/vercel.json", "evaluation/oracle/independent_oracle.py"):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    # Hash inventories can randomly contain key-shaped bytes. The actual source
    # files remain scanned, so skipping generated inventories cannot hide a key.
    fake_key_shape = "sk-or-v1-" + "1234567890123456"
    (project / "MANIFEST.sha256").write_text("deadbeef " + fake_key_shape + "\n", encoding="utf-8")
    (project / "PACKAGE_FILE_LIST.csv").write_text("path,bytes\nMANIFEST.sha256,42\n", encoding="utf-8")
    preflight = _load_preflight()
    monkeypatch.setattr(preflight, "ROOT", project)
    assert preflight.run()["status"] == "PASS"
    (project / "leaked.txt").write_text(fake_key_shape, encoding="utf-8")
    assert "secret-pattern:leaked.txt" in preflight.run()["problems"]


def test_deployment_preflight_excludes_only_its_explicit_output_path(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    for relative in ("render.yaml", "deployment/render_start.py", "frontend/vercel.json", "evaluation/oracle/independent_oracle.py"):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    fake_key_shape = "sk-or-v1-" + "1234567890123456"
    output = project / "verification" / "deployment_preflight.json"
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps({"warning": fake_key_shape}), encoding="utf-8")
    preflight = _load_preflight()
    monkeypatch.setattr(preflight, "ROOT", project)
    assert preflight.run(excluded_paths={output})["status"] == "PASS"
    assert "secret-pattern:verification/deployment_preflight.json" in preflight.run()["problems"]
