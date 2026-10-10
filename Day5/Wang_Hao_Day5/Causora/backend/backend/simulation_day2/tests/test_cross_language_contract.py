"""Structural parity checks against the actual owner-supplied TypeScript contract.

Not a TypeScript parser: it checks top-level property names of selected DTOs.
The front-end's own tsc and runtime tests remain the authoritative TS checks.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from simulation_day1 import wire_models as wire

ROOT = Path(__file__).resolve().parents[2]
TS = (ROOT / "lib/contracts.ts").read_text(encoding="utf-8")
TYPES = (ROOT / "lib/types.ts").read_text(encoding="utf-8")


def ts_fields(type_name: str) -> set[str]:
    """Extract level-one properties from one TS type declaration, not inner objects."""
    match = re.search(r"export type " + re.escape(type_name) + r"\s*=\s*\{", TS)
    if not match:
        raise AssertionError(f"Missing shared TS type: {type_name}")
    depth, chunks, current = 1, [], ""
    for char in TS[match.end():]:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                chunks.append(current)
                break
        if char == ";" and depth == 1:
            chunks.append(current)
            current = ""
        else:
            current += char
    if depth != 0:
        raise AssertionError(f"Unclosed TS type: {type_name}")
    names = set()
    for chunk in chunks:
        chunk = re.sub(r"/\*.*?\*/", "", chunk, flags=re.S)
        chunk = re.sub(r"//[^\n]*", "", chunk)
        field = re.match(r"\s*([A-Za-z]\w*)\??\s*:", chunk)
        if field:
            names.add(field.group(1))
    return names


class ContractFieldParityTests(unittest.TestCase):
    def test_shared_scenario_contract_cells_request_and_error_fields(self):
        pairs = {
            "Scenario": wire.Scenario,
            "DecisionOption": wire.DecisionOption,
            "ContractConstraint": wire.ContractConstraint,
            "CostBreakdown": wire.CostBreakdown,
            "MetricCell": wire.MetricCell,
            "SimulationResult": wire.SimulationResult,
            "DecisionDelta": wire.DecisionDelta,
            "SimulateRequest": wire.SimulateRequest,
            "SimulateResponse": wire.SimulateResponse,
            "ApiError": wire.ApiError,
            "ApiFailure": wire.ApiFailure,
        }
        for name, model in pairs.items():
            with self.subTest(type=name):
                self.assertEqual(ts_fields(name), set(model.model_fields))
        self.assertIn('from "./contracts"', TYPES)


if __name__ == "__main__":
    unittest.main()
