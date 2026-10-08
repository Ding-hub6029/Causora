"""Freeze a typed view of the already-shipped 104 weekly synthetic observations.

This does NOT derive the 26,000-unit renewal forecast from historical totals.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public" / "demo" / "historical_demand.csv"
DEST = Path(__file__).parent / "historical_weekly_v1.json"


def prepare_history() -> dict:
    raw = SOURCE.read_bytes()
    with SOURCE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["week_start", "units_demanded", "provenance"]:
            raise ValueError("Unexpected historical-demand CSV header")
        rows = list(reader)
    if len(rows) != 104:
        raise ValueError("104 complete weeks required")
    observations = []
    for index, row in enumerate(rows):
        if not row["units_demanded"].isdigit() or row["provenance"] != "synthetic_day1_fixture":
            raise ValueError(f"Invalid provenance or units at week {index}")
        week = date.fromisoformat(row["week_start"])
        if week != date(2024, 10, 7) + timedelta(weeks=index):
            raise ValueError(f"Gap or duplicate week at {index}")
        observations.append({"weekStart": week.isoformat(), "unitsDemanded": int(row["units_demanded"]),
                             "provenance": row["provenance"]})
    total = sum(o["unitsDemanded"] for o in observations)
    return {"dataVersion": "demo-2026.10.04-v4", "sourceFile": "public/demo/historical_demand.csv",
            "sourceSha256": hashlib.sha256(raw).hexdigest(), "provenance": "synthetic_day1_fixture",
            "weekCount": len(observations), "totalUnits": total, "meanWeeklyUnits": total / len(observations),
            "lockedForecastUnits24m": 26000,
            "lockedForecastProvenance": "Synthetic renewal-cycle forecast assumption: supplier_a_agreement.pdf p.4 and baseline contract.lockedForecastUnits24m; NOT the sum of historical demand",
            "observations": observations}


if __name__ == "__main__":
    snapshot = prepare_history()
    DEST.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{DEST}: {snapshot['weekCount']} weeks, {snapshot['totalUnits']} historical units, 26000 distinct locked-forecast assumption")
