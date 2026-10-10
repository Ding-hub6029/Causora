"""Rebuild only internal Day 3 schemas; shared public contracts stay unchanged."""
from __future__ import annotations

import json
from pathlib import Path

from simulation_day3.models import MonteCarloPreview
from simulation_day3.policy import Day3Policy

OUT = Path(__file__).parent / "schemas"


def emit() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, model in (
        ("unapproved_mc_policy.schema.json", Day3Policy),
        ("internal_mc_preview.schema.json", MonteCarloPreview),
    ):
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "$id": f"https://causora.example/day3-internal/{name}",
                  **model.model_json_schema()}
        (OUT / name).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(OUT / name)


if __name__ == "__main__":
    emit()
