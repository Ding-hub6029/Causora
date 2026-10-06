"""Structural JSON Schemas for the v4.1 wire adapter; TS validator remains semantic authority."""
from __future__ import annotations

import json
from pathlib import Path

EVIDENCE = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://causora.example/schemas/frontend-evidence-v4.1.json",
    "title": "Causora v4.1 frontend EvidenceRecord",
    "type": "object", "additionalProperties": False,
    "required": ["id", "sourceFile", "page", "quote", "locatorBbox", "extractedField",
                 "extractedValue", "matchMethod", "matchScore", "quoteMatched"],
    "properties": {
        "id": {"type": "string", "pattern": "^EV-[0-9]{3}$"},
        "sourceFile": {"type": "string", "pattern": "^[A-Za-z0-9_.-]+\\.pdf$"},
        "page": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 5},
        "locatorBbox": {"oneOf": [{"type": "null"}, {"type": "array", "minItems": 4, "maxItems": 4,
                         "items": {"type": "number", "minimum": 0}}]},
        "extractedField": {"type": "string", "enum": ["renewal_notice_days", "renewal_term_months",
                           "renewal_price_increase_pct", "min_purchase_share_A", "termination_fee"]},
        "extractedValue": {"type": "string", "minLength": 1},
        "matchMethod": {"type": "string", "enum": ["exact", "fuzzy"]},
        "matchScore": {"type": "number", "minimum": 0, "maximum": 1},
        "quoteMatched": {"type": "boolean"},
    },
}

# This schema describes *this frozen LOCAL MOCK* only, not all SimulationResult
# responses. A genuinely executed deterministic simulator can also report
# monteCarloRuns=0; use execution provenance to distinguish it from a mock.
MOCK = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Causora v4.1 LOCAL MOCK wire shape (structural subset)",
    "type": "object", "additionalProperties": False,
    "required": ["meta", "intake", "evidence", "contract", "variables", "scenarios", "options",
                 "simulation", "boardroom", "critic", "brief"],
    "$defs": {"evidence": {k: v for k, v in EVIDENCE.items() if not k.startswith("$")}},
    "properties": {
        "meta": {"type": "object", "required": ["schemaVersion", "dataVersion", "status", "notice"],
                 "properties": {"schemaVersion": {"const": "causora.contract.v1"},
                                "dataVersion": {"type": "string", "minLength": 1},
                                "status": {"type": "string", "pattern": "LOCAL MOCK"},
                                "notice": {"type": "string", "pattern": "LOCAL MOCK"}}},
        "intake": {"type": "array", "minItems": 4, "maxItems": 4},
        "evidence": {"type": "array", "minItems": 5, "maxItems": 5, "items": {"$ref": "#/$defs/evidence"}},
        "contract": {"type": "object"}, "variables": {"type": "array"},
        "scenarios": {"type": "array", "minItems": 3, "maxItems": 3},
        "options": {"type": "array", "minItems": 3, "maxItems": 3},
        "simulation": {"type": "object", "required": ["dataVersion", "matrix", "monteCarloRuns"],
                       "properties": {"dataVersion": {"type": "string"}, "matrix": {"type": "object"},
                                      "monteCarloRuns": {"const": 0}}},
        "boardroom": {"type": "array", "minItems": 3, "maxItems": 3},
        "critic": {"type": "object"}, "brief": {"type": "object"},
    },
}


def main() -> None:
    folder = Path("demo_data/integration_v4.1")
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in (("frontend_evidence.schema.json", EVIDENCE),
                       ("frontend_compatible_local_mock.schema.json", MOCK)):
        (folder / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("Wrote two structural v4.1 wire schemas (semantic checks require Python + baseline TS validator)")


if __name__ == "__main__":
    main()
