"""Regression tests for the isolated unreviewed deterministic development runner.

The fixture deliberately runs Jinzhu's public unreviewed preview entry point and the
independent trace audit.  It never turns the preview into the old Day 3 mock matrix.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest

from agent_day3.dev_bridge import build_development_bundle
from agent_day3.dev_roles import (
    DevClaimStubProvider,
    build_claim_catalog,
    build_dev_projections,
    run_dev_parallel,
)
from agent_day3.wire_models import sha256_json


DEFAULT_JINZHU_ROOT = Path("/home/ubuntu/causora/compat-context/jinzhu/causora")


@pytest.fixture(scope="session")
def jinzhu_root() -> Path:
    root = Path(os.environ.get("CAUSORA_JINZHU_ROOT", DEFAULT_JINZHU_ROOT)).expanduser().resolve()
    if not (root / "simulation_day2" / "deterministic.py").is_file():
        pytest.skip("Set CAUSORA_JINZHU_ROOT to the actual Jinzhu causora source root")
    return root


@pytest.fixture(scope="session")
def audited_bundle(jinzhu_root: Path) -> dict[str, Any]:
    return build_development_bundle(jinzhu_root, enabled=True)


@pytest.fixture
def bundle(audited_bundle: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(audited_bundle)


def _selection(role: str, payload: dict[str, Any], *, status: str = "Watch") -> dict[str, Any]:
    return {"role": role, "claim_ids": [payload["claimCatalog"][0]["id"]], "status": status}


def test_actual_preview_builds_narrow_typed_projections_and_code_catalog(bundle: dict[str, Any]) -> None:
    lineage_without_version = {
        key: value for key, value in bundle["lineage"].items() if key != "analysisDataVersion"
    }
    assert bundle["sourceMode"] == "UNREVIEWED_DEV_COMPUTED"
    assert bundle["humanReviewStatus"] == "pending"
    assert bundle["decisionReady"] is False
    assert bundle["traceAudit"]["matrixCells"] == 9
    assert bundle["traceAudit"]["traceRows"] == 936
    assert bundle["lineage"]["candidateDataVersion"] != bundle["lineage"]["engineSourceDataVersion"]
    assert bundle["lineage"]["engineSourceDataVersion"] == bundle["preview"]["sourceDataVersion"]
    assert bundle["lineage"]["analysisDataVersion"] == (
        "dev-analysis-" + sha256_json(lineage_without_version)[:20]
    )
    views = build_dev_projections(bundle)
    assert set(views) == {"CFO", "COO", "Risk"}
    assert views["CFO"].options[0].tcoUsd == bundle["preview"]["matrix"]["demand-drop"][0]["tcoUsd"]
    assert not hasattr(views["COO"].options[0], "cashOutflowUsd")
    assert not hasattr(views["Risk"].options[0], "tcoUsd")
    assert not hasattr(views["Risk"], "evidence")
    coo_ids = {claim.id for claim in build_claim_catalog(views["COO"])}
    assert "coo_purchases_exceed_demand" in coo_ids
    assert "coo_purchases_equal_demand" not in coo_ids
    risk_ids = {claim.id for claim in build_claim_catalog(views["Risk"])}
    assert {"risk_deterministic_no_probabilistic_tail", "risk_locked_floor_under_declining_demand",
            "risk_conditional_renewed_exit_fee"} <= risk_ids


def test_requires_explicit_enablement(bundle: dict[str, Any]) -> None:
    with pytest.raises(PermissionError, match="enabled=True"):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider()))


@pytest.mark.parametrize("key,value", [
    ("humanReviewStatus", "approved"),
    ("decisionReady", True),
    ("permittedUse", "LIVE"),
    ("sourceMode", "SIMULATION_READY"),
])
def test_pending_gate_flags_cannot_be_changed(bundle: dict[str, Any], key: str, value: Any) -> None:
    bundle[key] = value
    with pytest.raises(ValueError):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))


def test_preview_review_flags_and_audit_coverage_cannot_be_promoted_or_skipped(bundle: dict[str, Any]) -> None:
    bundle["preview"]["reviewStatus"] = "SELF_ATTESTED_SYNTHETIC_REVIEW"
    with pytest.raises(ValueError):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))

    bundle = copy.deepcopy(bundle)
    bundle["preview"]["reviewStatus"] = "PENDING_HUMAN_REVIEW"
    bundle["traceAudit"]["traceRows"] = 0
    with pytest.raises(ValueError):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))


def test_hash_and_source_hash_mismatch_are_rejected_before_provider_call(bundle: dict[str, Any]) -> None:
    original = copy.deepcopy(bundle)
    bundle["preview"]["inputHashesSha256"]["historicalDemand"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))

    bundle = copy.deepcopy(original)
    bundle["lineage"]["requestSha256"] = "f" * 64
    bundle["lineage"]["analysisDataVersion"] = "dev-analysis-" + sha256_json({
        key: value for key, value in bundle["lineage"].items() if key != "analysisDataVersion"
    })[:20]
    with pytest.raises(ValueError, match="request hash"):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))

    bundle = copy.deepcopy(original)
    bundle["evidence"][0]["extractedField"] = "tampered-but-still-shaped"
    with pytest.raises(ValueError, match="evidence hash"):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))

    bundle = copy.deepcopy(original)
    bundle["traceAudit"]["checks"] = {"tampered": True}
    with pytest.raises(ValueError, match="trace-audit hash"):
        asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))


def test_live_provider_kind_never_makes_live_output(bundle: dict[str, Any]) -> None:
    class LiveNamedProvider(DevClaimStubProvider):
        kind = "LIVE"

    result = asyncio.run(run_dev_parallel(bundle, provider=LiveNamedProvider(), enabled=True))
    assert result["providerKind"] == "LIVE"
    assert {output["availability"] for output in result["outputs"]} == {"DEV_ONLY"}
    assert result["decisionReady"] is False
    assert result["sourceMode"] == "UNREVIEWED_DEV_COMPUTED"


def test_provider_payload_has_no_matrix_trace_paths_quotes_receipts_or_cross_role_values(bundle: dict[str, Any]) -> None:
    class InspectingProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system
            serialized = json.dumps(payload, sort_keys=True).casefold()
            for forbidden in ("fullmatrix", "weeklytrace", "sourcepath", "sourcefile", "pdfquote", "humanreceipt"):
                assert forbidden not in serialized
            assert set(payload) == {
                "role", "view", "claimCatalog", "commentaryMode", "humanReviewStatus", "decisionReady"
            }
            assert payload["role"] == role
            assert payload["view"]["role"] == role
            assert payload["view"]
            assert payload["claimCatalog"]
            assert all(set(claim) == {"id", "statementTemplate", "metricRefs", "evidenceIds"}
                       for claim in payload["claimCatalog"])
            assert set(schema["properties"]) == {"role", "claim_ids", "status"}
            if role == "CFO":
                assert isinstance(payload["view"]["options"][0]["tcoUsd"], int)
                for forbidden in ("stockoutprobability", "orderedunits", "deliveredunits", "servicelevel", "contract"):
                    assert forbidden not in serialized
                assert all(not claim["evidenceIds"] for claim in payload["claimCatalog"])
            elif role == "COO":
                assert isinstance(payload["view"]["options"][0]["orderedUnitsA"], int)
                assert isinstance(payload["view"]["options"][0]["serviceLevel"], float)
                for forbidden in ("tco", "cash", "financial", "contract"):
                    assert forbidden not in serialized
                assert all(not claim["evidenceIds"] for claim in payload["claimCatalog"])
            else:
                assert isinstance(payload["view"]["contract"]["terminationFeeUsd"], int)
                assert isinstance(payload["view"]["options"][0]["cashOutflowUsd"], int)
                for forbidden in ("tco", "revenue", "grossprofit", "orderedunits", "deliveredunits",
                                  "endinginventory", "unitstransit", "fulfilledunits", "lostunits", "servicelevel"):
                    assert forbidden not in serialized
            return _selection(role, payload)

    result = asyncio.run(run_dev_parallel(bundle, provider=InspectingProvider(), enabled=True))
    assert result["state"] == "ALL_READY"
    assert "sourceHashMapping" not in result["lineage"]
    assert "backendPath" not in json.dumps(result["lineage"], sort_keys=True)


def test_parallel_barrier_starts_each_role_before_waiting(bundle: dict[str, Any]) -> None:
    class BarrierProvider:
        kind = "TEST_DOUBLE"

        def __init__(self) -> None:
            self.arrived: list[str] = []
            self.release = asyncio.Event()

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            self.arrived.append(role)
            if len(self.arrived) == 3:
                self.release.set()
            await asyncio.wait_for(self.release.wait(), timeout=1)
            return _selection(role, payload)

    provider = BarrierProvider()
    result = asyncio.run(run_dev_parallel(bundle, provider=provider, enabled=True))
    assert provider.arrived == ["CFO", "COO", "Risk"]
    assert result["state"] == "ALL_READY"


def test_timeout_error_and_provider_cancellation_are_role_isolated(bundle: dict[str, Any]) -> None:
    class MixedProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            if role == "CFO":
                await asyncio.sleep(0.05)
            elif role == "COO":
                raise RuntimeError("provider failure")
            else:
                raise asyncio.CancelledError
            return _selection(role, payload)

    result = asyncio.run(run_dev_parallel(bundle, provider=MixedProvider(), enabled=True, timeout_seconds=0.001))
    assert result["state"] == "UNAVAILABLE"
    assert [output["failure"] for output in result["outputs"]] == ["timeout", "provider_error", "cancelled"]
    assert {output["availability"] for output in result["outputs"]} == {"UNAVAILABLE"}


def test_outer_cancellation_propagates(bundle: dict[str, Any]) -> None:
    class HangingProvider:
        kind = "TEST_DOUBLE"

        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def complete(self, *, role, system, payload, schema):
            del role, system, payload, schema
            self.started.set()
            await self.release.wait()
            raise AssertionError("outer cancellation should arrive first")

    async def exercise() -> None:
        provider = HangingProvider()
        task = asyncio.create_task(run_dev_parallel(bundle, provider=provider, enabled=True))
        await provider.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())


def test_unknown_false_claim_and_unexpected_reason_text_are_invalid(bundle: dict[str, Any]) -> None:
    class BadClaimProvider:
        kind = "TEST_DOUBLE"

        async def complete(self, *, role, system, payload, schema):
            del system, schema
            if role == "COO":
                # Actual audited demand-drop data has excess purchases, not exact equality.
                return {"role": role, "claim_ids": ["coo_purchases_equal_demand"], "status": "Watch"}
            if role == "Risk":
                return {**_selection(role, payload), "reason_text": "provider prose is forbidden"}
            return _selection(role, payload)

    result = asyncio.run(run_dev_parallel(bundle, provider=BadClaimProvider(), enabled=True))
    assert result["state"] == "PARTIAL"
    assert result["outputs"][0]["failure"] is None
    assert result["outputs"][1]["failure"] == "invalid_response"
    assert result["outputs"][2]["failure"] == "invalid_response"


def test_bindings_are_actual_numbers_and_cover_every_selected_reference(bundle: dict[str, Any]) -> None:
    result = asyncio.run(run_dev_parallel(bundle, provider=DevClaimStubProvider(), enabled=True))
    cfo = result["outputs"][0]
    expected = bundle["preview"]["matrix"]["demand-drop"][0]["tcoUsd"]
    assert cfo["metricBindings"]["tcoUsd:D0"] == expected
    assert type(cfo["metricBindings"]["tcoUsd:D0"]) is int
    assert set(cfo["metricBindings"]) == set(cfo["metricRefs"])
    coo = result["outputs"][1]
    cell = bundle["preview"]["matrix"]["demand-drop"][0]
    assert coo["metricBindings"]["orderedUnitsA:D0"] == cell["orderedUnitsA"]
    assert type(coo["metricBindings"]["orderedUnitsA:D0"]) is int
    risk = result["outputs"][2]
    assert "risk_deterministic_no_probabilistic_tail" in risk["claimIds"]
    assert risk["metricBindings"]["policy.monteCarloRuns"] == 0
