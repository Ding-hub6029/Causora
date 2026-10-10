"""Cross-check an untrusted v1 SimulateSuccess against its request and contract.

This does not infer Monte Carlo probabilities or independently recreate weekly
physical results; it catches arithmetic/selection substitution at the boundary.
It intentionally does NOT call the response builder's delta/selection helpers.
"""
from __future__ import annotations

import json
import math

from simulation_day1.interfaces import ContractInputError, check_accounting, validate_request
from simulation_day1.wire_models import SimulateSuccess


class NumericMismatch(ValueError):
    pass


def validate_simulation_response(response: dict, request: dict, contract: dict,
                                 *, expected_data_version: str,
                                 allow_legacy_mock_for_tests: bool = False) -> None:
    """Fail closed on changed cells, deltas, winner, violations or provenance."""
    try:
        typed = SimulateSuccess.model_validate_json(json.dumps(response, ensure_ascii=False, allow_nan=False))
        validate_request(request, contract=contract, allow_unfrozen_scenarios=True)
        simulation = typed.data.simulation
        if (response["dataVersion"] != expected_data_version or simulation.dataVersion != expected_data_version or
                simulation.seed != request["seed"] or simulation.formulaVersion != "tco-v1" or
                simulation.weeks != 104 or not simulation.simulationId):
            raise NumericMismatch("simulation metadata differs from input or immutable dataset")
        if allow_legacy_mock_for_tests:
            if simulation.monteCarloRuns != 0 or "mock" not in simulation.simulationId:
                raise NumericMismatch("legacy mock option is restricted to frozen Day 1 test vectors")
        elif simulation.monteCarloRuns <= 0 or "mock" in simulation.simulationId:
            raise NumericMismatch("an MC probability/P90 cannot be claimed from a zero-draw deterministic or mock run")
        check_accounting(simulation.model_dump(mode="json"), contract, request["options"])
        expected_ids = {s["id"] for s in request["scenarios"]}
        if set(simulation.matrix) != expected_ids or set(typed.data.selections) != expected_ids:
            raise NumericMismatch("scenario set does not match the request")
        by_delta = {(row.scenarioId, row.optionId): row for row in typed.data.deltas}
        if len(by_delta) != 9:
            raise NumericMismatch("duplicate or missing scenario-option delta")
        for scenario_id in expected_ids:
            rows = {cell.optionId: cell for cell in simulation.matrix[scenario_id]}
            if set(rows) != {"D0", "D1", "D2"}:
                raise NumericMismatch(f"{scenario_id}: duplicate or missing option")
            base = rows["D0"]
            eligible = []
            expected_violations = []
            for oid in ("D0", "D1", "D2"):
                cell = rows[oid]
                delta = by_delta.get((scenario_id, oid))
                if delta is None or delta.baselineOptionId != "D0":
                    raise NumericMismatch(f"{scenario_id}/{oid}: missing or wrong baseline delta")
                integers = (delta.deltaTco == cell.expectedTco - base.expectedTco and
                            delta.deltaCashP90 == cell.cashOutflowP90 - base.cashOutflowP90)
                fractions = (math.isfinite(delta.deltaStockoutPp) and math.isfinite(delta.deltaServicePp) and
                             math.isclose(delta.deltaStockoutPp, 100 * (cell.stockoutProbability - base.stockoutProbability), rel_tol=0, abs_tol=1e-8) and
                             math.isclose(delta.deltaServicePp, 100 * (cell.serviceLevel - base.serviceLevel), rel_tol=0, abs_tol=1e-8))
                if not integers or not fractions:
                    raise NumericMismatch(f"{scenario_id}/{oid}: delta is not option minus D0 (pp for probabilities)")
                if not cell.feasible:
                    expected_violations.append((oid, "infeasible"))
                if cell.stockoutProbability > request["riskThreshold"]:
                    expected_violations.append((oid, "stockout_threshold"))
                if cell.cashOutflowP90 > request["budgetCeilingUsd"]:
                    expected_violations.append((oid, "cash_ceiling"))
                if cell.feasible and cell.stockoutProbability <= request["riskThreshold"] and cell.cashOutflowP90 <= request["budgetCeilingUsd"]:
                    eligible.append(cell)
            selection = typed.data.selections[scenario_id]
            observed_violations = [(v.optionId, v.code) for v in selection.constraintViolations]
            winner = min(eligible, key=lambda x: (x.expectedTco, x.optionId)).optionId if eligible else None
            if (selection.scenarioId != scenario_id or selection.recommendedOptionId != winner or
                    selection.status != ("selected" if winner else "no_feasible_option") or
                    observed_violations != expected_violations):
                raise NumericMismatch(f"{scenario_id}: recommendation/ordered violations contradict matrix and request")
    except (ContractInputError, TypeError, ValueError, KeyError) as exc:
        if isinstance(exc, NumericMismatch):
            raise
        raise NumericMismatch(f"invalid or inconsistent v1 simulation response: {exc}") from exc
