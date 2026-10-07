"""Integration regressions for the independent Day 3 development trace audit.

The real engine is used only to construct a public unreviewed preview fixture.  The
module under test never invokes its private calculation helpers; mutations retain
the original preview ID to prove that trace and summary checks are independent of
metadata alone.
"""
from __future__ import annotations

import copy
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from agent_day3.dev_trace_validation import TraceMismatch, audit_deterministic_preview


DEFAULT_JINZHU_ROOT = Path("/home/ubuntu/causora/compat-context/jinzhu/causora")


@pytest.fixture(scope="session")
def jinzhu_root() -> Path:
    """Resolve an explicitly configured real Jinzhu source root or skip integration."""
    configured = os.environ.get("CAUSORA_JINZHU_ROOT")
    root = Path(configured).expanduser() if configured else DEFAULT_JINZHU_ROOT
    if not (root / "simulation_day2" / "deterministic.py").is_file():
        pytest.skip(
            "Jinzhu integration source is unavailable; set CAUSORA_JINZHU_ROOT to its causora root. "
            "The audit must not pass against a substitute fixture."
        )
    try:
        import openpyxl  # noqa: F401 - deterministic's source reader needs it.
        import pydantic  # noqa: F401 - strict Jinzhu DTOs need it.
    except ImportError as exc:
        pytest.skip(f"Jinzhu integration dependency is unavailable: {exc}")
    return root.resolve()


@pytest.fixture(scope="session")
def real_inputs(jinzhu_root: Path) -> tuple[dict, dict, dict]:
    request = json.loads((jinzhu_root / "simulation_day1/examples/simulate_request.json").read_text(encoding="utf-8"))
    policy = json.loads((jinzhu_root / "simulation_day2/examples/UNAPPROVED_TEST_POLICY.json").read_text(encoding="utf-8"))
    mock = json.loads((jinzhu_root / "demo_data/causora_day1_mock.json").read_text(encoding="utf-8"))
    return request, policy, mock["contract"]


@pytest.fixture(scope="session")
def real_preview(jinzhu_root: Path, real_inputs: tuple[dict, dict, dict]) -> dict:
    """Generate test input through the public engine entry point, never a private oracle."""
    if str(jinzhu_root) not in sys.path:
        sys.path.insert(0, str(jinzhu_root))
    deterministic = importlib.import_module("simulation_day2.deterministic")
    request, policy, _contract = real_inputs
    return deterministic.run_unreviewed_preview(copy.deepcopy(request), copy.deepcopy(policy), project_root=jinzhu_root)


def _assert_rejected(preview: dict, real_inputs: tuple[dict, dict, dict], jinzhu_root: Path,
                     *, policy: dict | None = None) -> None:
    request, real_policy, contract = real_inputs
    with pytest.raises((TraceMismatch, ValueError)):
        audit_deterministic_preview(
            preview,
            copy.deepcopy(request),
            copy.deepcopy(real_policy if policy is None else policy),
            copy.deepcopy(contract),
            jinzhu_root,
        )


def test_real_engine_preview_passes_full_independent_trace_audit(
    real_preview: dict, real_inputs: tuple[dict, dict, dict], jinzhu_root: Path
) -> None:
    request, policy, contract = real_inputs
    result = audit_deterministic_preview(
        copy.deepcopy(real_preview), copy.deepcopy(request), copy.deepcopy(policy), copy.deepcopy(contract), jinzhu_root
    )
    assert result["kind"] == "CAUSORA_DAY3_DEV_ONLY_TRACE_AUDIT_V1"
    assert result["devOnly"] is True
    assert result["decisionReady"] is False
    assert result["matrixCells"] == 9
    assert result["traceRows"] == 936
    assert len(result["checks"]) >= 8
    assert {(row["scenarioId"], row["optionId"]) for row in result["cells"]} == {
        (scenario, option) for scenario in ("baseline", "demand-drop", "lead-stress") for option in ("D0", "D1", "D2")
    }


def test_real_trace_is_not_the_day1_mock_matrix(
    real_preview: dict, real_inputs: tuple[dict, dict, dict], jinzhu_root: Path
) -> None:
    """Prove the test data is the genuine trace preview, rather than a mock-matrix lookalike."""
    mock = json.loads((jinzhu_root / "demo_data/causora_day1_mock.json").read_text(encoding="utf-8"))
    trace_cell = real_preview["matrix"]["baseline"][0]
    mock_cell = mock["simulation"]["matrix"]["baseline"][0]
    assert "weeklyTrace" in trace_cell and len(trace_cell["weeklyTrace"]) == 104
    assert "weeklyTrace" not in mock_cell
    assert "stockoutProbability" not in trace_cell and "cashOutflowP90" not in trace_cell
    assert "stockoutProbability" in mock_cell and "cashOutflowP90" in mock_cell
    request, policy, contract = real_inputs
    assert real_preview["previewId"] != mock["simulation"]["simulationId"]
    assert audit_deterministic_preview(real_preview, request, policy, contract, jinzhu_root)["matrixCells"] == 9


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(lambda preview: preview["matrix"]["baseline"][0]["weeklyTrace"][0].__setitem__("openingUnits", 999), id="trace"),
        pytest.param(lambda preview: preview["matrix"]["baseline"][0].__setitem__("tcoUsd", preview["matrix"]["baseline"][0]["tcoUsd"] + 1), id="summary"),
        pytest.param(lambda preview: preview["matrix"]["baseline"][0]["weeklyTrace"][1].__setitem__("arrivalsA", 1), id="arrivals"),
        pytest.param(lambda preview: preview["inputHashesSha256"].__setitem__("historicalDemand", "0" * 64), id="source-hash"),
        pytest.param(lambda preview: preview["matrix"]["baseline"][0].__setitem__("grossMargin", 0.123456), id="margin"),
        pytest.param(lambda preview: preview.__setitem__("seed", preview["seed"] + 1), id="seed"),
        pytest.param(lambda preview: preview.__setitem__("internalSchemaVersion", "wrong.schema.v0"), id="schema"),
        pytest.param(lambda preview: preview["matrix"]["baseline"][0].__setitem__("stockoutOccurred", not preview["matrix"]["baseline"][0]["stockoutOccurred"]), id="stockout-boolean"),
    ],
)
def test_same_id_mutations_are_rejected_independently(
    mutation, real_preview: dict, real_inputs: tuple[dict, dict, dict], jinzhu_root: Path
) -> None:
    preview = copy.deepcopy(real_preview)
    original_id = preview["previewId"]
    mutation(preview)
    assert preview["previewId"] == original_id, "mutation must not rely on an altered preview ID"
    _assert_rejected(preview, real_inputs, jinzhu_root)


def test_missing_or_duplicate_matrix_cell_is_rejected(
    real_preview: dict, real_inputs: tuple[dict, dict, dict], jinzhu_root: Path
) -> None:
    missing = copy.deepcopy(real_preview)
    missing["matrix"]["baseline"].pop()
    _assert_rejected(missing, real_inputs, jinzhu_root)

    duplicate = copy.deepcopy(real_preview)
    duplicate["matrix"]["baseline"][2] = copy.deepcopy(duplicate["matrix"]["baseline"][1])
    _assert_rejected(duplicate, real_inputs, jinzhu_root)


def test_wrong_but_schema_valid_policy_is_rejected(
    real_preview: dict, real_inputs: tuple[dict, dict, dict], jinzhu_root: Path
) -> None:
    _request, policy, _contract = real_inputs
    wrong_policy = copy.deepcopy(policy)
    wrong_policy["targetStockUnits"] += 1
    _assert_rejected(copy.deepcopy(real_preview), real_inputs, jinzhu_root, policy=wrong_policy)
