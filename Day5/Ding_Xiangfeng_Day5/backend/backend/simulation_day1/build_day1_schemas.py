"""Generate schema artifacts and frozen internal fixture view without editing base files.

The generated API schemas are descriptive mirrors of lib/contracts.ts; the
baseline draft stays authoritative. No endpoint or live simulation is created.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook

from simulation_day1.prepare_history import prepare_history
from simulation_day1.source_models import DemoInputs
from simulation_day1.wire_models import (
    ApiFailure, BoardroomRequest, BoardroomSuccess, DatasetSuccess,
    EvidenceSuccess, GoldenSuccess, HealthSuccess, MockData,
    SimulateRequest, SimulateSuccess,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "simulation_day1"
SCHEMAS = OUT / "schemas"
FROZEN_SOURCE_HASHES = {
    "public/demo/historical_demand.csv": "654a22f3f5433e214611f3c5a69b625bedad2d11157dedfa9cd65bbb14d3499e",
    "public/demo/supplier_delivery_history.xlsx": "cabeaae5d3a9ba23f863734fca3b3080bc85d121b0dba75a7f6457fa76c56298",
    "public/demo/opening_inventory.csv": "c2ad7ff5d928623f69d2599fea47d20c008c3b1fdd4d3879d29dcc2799ffe067",
    "public/demo/supplier_correspondence_log.csv": "25dcd672d60ff549d870f4b7169f9df1f4b84e0320d8861f06de3b15b43e6952",
    "public/demo/supplier_a_agreement.pdf": "1e816c38cae6a045ef8b05426bb4c87ed160f119a52ac8adc65be074ef8c183f",
}


def source_hash(relative_path: str) -> str:
    digest = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
    if digest != FROZEN_SOURCE_HASHES[relative_path]:
        raise ValueError(f"Frozen synthetic source changed: {relative_path}; review and increment dataVersion before regeneration")
    return digest


def csv_rows(relative_path: str) -> list[dict[str, str]]:
    with (ROOT / relative_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_manifest() -> dict:
    history = prepare_history()
    if history["sourceSha256"] != FROZEN_SOURCE_HASHES[history["sourceFile"]]:
        raise ValueError("Frozen historical demand changed; review and increment dataVersion")
    delivery_file = "public/demo/supplier_delivery_history.xlsx"
    sheet = load_workbook(ROOT / delivery_file, read_only=True, data_only=True).active
    rows = sheet.values
    header = next(rows)
    if header != ("order_id", "supplier", "order_date", "arrival_date", "units", "base_price_usd", "provenance"):
        raise ValueError("Supplier file header changed")
    orders = []
    for order_id, supplier, order_date, arrival_date, units, base_price_usd, provenance in rows:
        orders.append({"orderId": order_id, "supplier": supplier, "orderDate": order_date,
                       "arrivalDate": arrival_date, "units": units, "basePriceUsd": float(base_price_usd),
                       "provenance": provenance})
    if len(orders) != 48:
        raise ValueError("Expected 48 synthetic supplier POs")
    inventory_file = "public/demo/opening_inventory.csv"
    inventory = csv_rows(inventory_file)
    if len(inventory) != 1:
        raise ValueError("Expected one SKU opening-inventory record")
    row = inventory[0]
    notice_file = "public/demo/supplier_correspondence_log.csv"
    notice = csv_rows(notice_file)
    if not notice:
        raise ValueError("Explicit notice register is missing")
    entries = [{"date": r["date"], "channel": r["channel"], "recipient": r["recipient"],
                "event": r["event"], "validWrittenNonrenewalNotice": {"true": True, "false": False}[r["valid_written_nonrenewal_notice"].lower()],
                "provenance": r["provenance"]} for r in notice]
    contract_file = "public/demo/supplier_a_agreement.pdf"
    baseline = json.loads((ROOT / "demo_data/causora_day1_mock.json").read_text(encoding="utf-8"))
    source = {
        "dataVersion": baseline["meta"]["dataVersion"],
        "fixtureStatus": "synthetic_local_mock_not_engine_input_verified",
        "historicalDemand": history,
        "supplierDelivery": {"sourceFile": delivery_file, "sourceSha256": source_hash(delivery_file),
                             "orderCount": len(orders), "orders": orders},
        "openingInventory": {"sourceFile": inventory_file, "sourceSha256": source_hash(inventory_file),
                             "asOfDate": row["as_of_date"], "sku": row["sku"],
                             "unitsOnHand": int(row["units_on_hand"]), "provenance": row["provenance"]},
        "noticeRegister": {"sourceFile": notice_file, "sourceSha256": source_hash(notice_file),
                           "noticeSent": baseline["contract"]["noticeSent"], "entries": entries},
        "contractAssumptions": {"sourceFile": contract_file, "sourceSha256": source_hash(contract_file),
                                "evidencePage": 4, "forecastBasis": baseline["contract"]["forecastBasis"],
                                "lockedForecastUnits24m": baseline["contract"]["lockedForecastUnits24m"],
                                "forecastSource": "Synthetic renewal-cycle forecast: agreement PDF p.4 and baseline contract, not derived from historical demand",
                                "humanReviewed": False, "status": "quote_matched_synthetic_not_human_reviewed"},
    }
    # JSON mode applies strict date parsing and preserves ISO dates when serialized.
    return DemoInputs.model_validate_json(json.dumps(source)).model_dump(mode="json")


def emit() -> None:
    manifest = build_manifest()
    (OUT / "demo_inputs_v1.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    targets = {
        "demo_inputs_v1.schema.json": DemoInputs,
        "mock_data_v1.schema.json": MockData,
        "simulate_request_v1.schema.json": SimulateRequest,
        "simulate_success_v1.schema.json": SimulateSuccess,
        "dataset_success_v1.schema.json": DatasetSuccess,
        "boardroom_request_v1.schema.json": BoardroomRequest,
        "boardroom_success_v1.schema.json": BoardroomSuccess,
        "evidence_success_v1.schema.json": EvidenceSuccess,
        "health_success_v1.schema.json": HealthSuccess,
        "golden_success_v1.schema.json": GoldenSuccess,
        "api_failure_v1.schema.json": ApiFailure,
    }
    for name, model in targets.items():
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        # Informational only; no published endpoint is implied by this URI.
        schema["$id"] = "https://causora.example/day1-schemas/" + name
        (SCHEMAS / name).write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated internal demo manifest and {len(targets)} strict DTO schemas; no backend call.")


if __name__ == "__main__":
    emit()
