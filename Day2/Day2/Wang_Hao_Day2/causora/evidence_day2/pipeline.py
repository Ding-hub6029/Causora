"""Day 2 synthetic contract -> evidence -> human review -> typed dataset DTO.

NO automatic approval, NO simulation, NO HTTP server. The Day 1 PDF matcher and
Jinzhu's Day 1 wire types are reused without modifying either owner's source.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pymupdf
from pydantic import ValidationError

from causora_day1.adapter import FRONT_IDS, front_value
from causora_day1.evidence import extract_baseline, verify_source
from causora_day1.schemas import BusinessVariable as InternalBusinessVariable
from causora_day1.schemas import EvidenceField, EvidenceSummary
from evidence_day2.handoff_models import JinzhuContractHandoff, validate_promoted_graph
from simulation_day1.build_day1_schemas import build_manifest
from simulation_day1.wire_models import ContractConstraint, DatasetSuccess, EvidenceSuccess

SCHEMA_VERSION = "causora.contract.v1"
BASELINE_VERSION = "demo-2026.10.04-v4"
FROZEN = {
    "public/demo/supplier_a_agreement.pdf": "1e816c38cae6a045ef8b05426bb4c87ed160f119a52ac8adc65be074ef8c183f",
    "demo_data/causora_day1_mock.json": "7002888a4d9f831a7210ec0dbf6cfd556c4c22a134d41e2f0d9674689ceddf56",
    "public/demo/supplier_correspondence_log.csv": "25dcd672d60ff549d870f4b7169f9df1f4b84e0320d8861f06de3b15b43e6952",
    "demo_data/supplier_correspondence_log.csv": "25dcd672d60ff549d870f4b7169f9df1f4b84e0320d8861f06de3b15b43e6952",
    "public/demo/historical_demand.csv": "654a22f3f5433e214611f3c5a69b625bedad2d11157dedfa9cd65bbb14d3499e",
    "public/demo/supplier_delivery_history.xlsx": "cabeaae5d3a9ba23f863734fca3b3080bc85d121b0dba75a7f6457fa76c56298",
    "public/demo/opening_inventory.csv": "c2ad7ff5d928623f69d2599fea47d20c008c3b1fdd4d3879d29dcc2799ffe067",
    "lib/contracts.ts": "2c4eb25fab520c76a8d0622df3425eea443d56440a067eafdd18f148c030176d",
}
ACK = "I reviewed each synthetic contract field and listed assumption; this is not real-world contract verification."
ASSUMPTION_KEYS = ("decisionDate", "renewalDate", "noticeSent", "forecastBasis", "lockedForecastUnits24m")
IMPLEMENTATION_FILES = (
    "evidence_day2/pipeline.py", "evidence_day2/cli.py", "evidence_day2/handoff_models.py",
    "evidence_day2/schemas/jinzhu_contract_input.schema.json",
    "causora_day1/claim_checks.py", "causora_day1/evidence.py",
    "causora_day1/schemas.py", "causora_day1/adapter.py", "simulation_day1/wire_models.py",
    "simulation_day1/source_models.py", "simulation_day1/build_day1_schemas.py",
    "simulation_day1/schemas/dataset_success_v1.schema.json",
    "simulation_day1/schemas/evidence_success_v1.schema.json",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def implementation_hashes() -> dict[str, str]:
    # These are the actual imported package files. Replacing the code or wire
    # schema after a person signs the review invalidates that review scope.
    root = Path(__file__).resolve().parents[1]
    return {name: hash_file(root / name) for name in IMPLEMENTATION_FILES}


def frozen_sources(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative, expected in FROZEN.items():
        actual = hash_file(root / relative)
        if actual != expected:
            raise ValueError(f"Frozen team input changed: {relative}; review and version the dataset before reuse")
        result[relative] = actual
    return result


def notice_state(root: Path, deadline: date) -> bool:
    # The synthetic register is a separate assumption; PDF text alone cannot
    # establish whether a real notice was or was not sent.
    with (root / "public/demo/supplier_correspondence_log.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = ["date", "channel", "recipient", "event", "valid_written_nonrenewal_notice", "provenance"]
        if reader.fieldnames != expected:
            raise ValueError("Notice register columns changed")
        rows = list(reader)
    if not rows or any(row["valid_written_nonrenewal_notice"] not in ("true", "false") or
                       row["provenance"] != "synthetic_mock_not_a_real_supplier_record" for row in rows):
        raise ValueError("Invalid or non-synthetic notice register")
    return any(row["valid_written_nonrenewal_notice"] == "true" and
               date.fromisoformat(row["date"]) <= deadline for row in rows)


def _assumptions(root: Path, baseline: dict) -> dict[str, Any]:
    contract = baseline["contract"]
    decision = date.fromisoformat(contract["decisionDate"])
    renewal = date.fromisoformat(contract["renewalDate"])
    deadline = renewal - timedelta(days=contract["renewalNoticeDays"])
    if (renewal - decision).days != contract["daysToRenewal"] or deadline.isoformat() != contract["noticeDeadline"]:
        raise ValueError("Synthetic dates/deadline disagree")
    sent = notice_state(root, deadline)
    if sent != contract["noticeSent"]:
        raise ValueError("Explicit synthetic notice register disagrees with baseline contract")
    pdf = root / "public/demo/supplier_a_agreement.pdf"
    with pymupdf.open(pdf) as doc:
        page = doc[3].get_text("text")
    if "forecast is fixed at 26,000 units" not in page or contract["lockedForecastUnits24m"] != 26000:
        raise ValueError("Locked forecast assumption absent from synthetic PDF/contract")
    if contract["forecastBasis"] != "locked-at-renewal":
        raise ValueError("Forecast basis changed; owner review required")
    return {key: contract[key] for key in ASSUMPTION_KEYS}


def prepare(root: Path) -> tuple[EvidenceSummary, dict, dict[str, Any], dict[str, str]]:
    root = root.resolve()
    source_hashes = frozen_sources(root)
    baseline = load_json(root / "demo_data/causora_day1_mock.json")
    if baseline["meta"]["schemaVersion"] != SCHEMA_VERSION or baseline["meta"]["dataVersion"] != BASELINE_VERSION:
        raise ValueError("Unknown Ding Day 2 frontend contract or dataset version")
    # Independently parse all five frozen synthetic source files using Jinzhu's
    # Day 1 typed source manifest. Its humanReviewed=false remains unmodified.
    manifest = build_manifest()
    if manifest != load_json(root / "simulation_day1/demo_inputs_v1.json"):
        raise ValueError("Jinzhu Day 1 source manifest no longer matches team inputs")
    for supplier in ("A", "B"):
        prices = {order["basePriceUsd"] for order in manifest["supplierDelivery"]["orders"]
                  if order["supplier"] == supplier}
        if prices != {baseline["simulation"]["unitPricesUsd"][supplier]}:
            raise ValueError(f"Supplier {supplier} price differs from frozen delivery inputs")
    summary = extract_baseline(root / "public/demo/supplier_a_agreement.pdf",
                               root / "demo_data/causora_day1_mock.json")
    verify_source(summary, root / "public/demo/supplier_a_agreement.pdf")
    if summary.dataset_id != "ds-001" or {r.id for r in summary.records} != set(FRONT_IDS) | {"EV-020"}:
        raise ValueError("Missing or duplicate frozen v4.1 claim ID")
    if any(not r.quote_matched or r.match_method != "exact" or r.page != 4 or r.manually_verified
           for r in summary.records) or summary.business_variables:
        raise ValueError("Day 2 review must begin from exact, unapproved, PDF-bound evidence")
    for rec in summary.records:
        if rec.id not in FRONT_IDS:
            continue
        front = next(e for e in baseline["evidence"] if e["id"] == rec.id)
        if (front["quote"] != rec.quote or front["sourceFile"] != rec.source_file or
            front["page"] != rec.page or front["extractedField"] != rec.extracted_field.value or
            front["extractedValue"] != front_value(rec)):
            raise ValueError(f"{rec.id}: baseline and PDF evidence differ")
    assumptions = _assumptions(root, baseline)
    return summary, baseline, assumptions, source_hashes


def _immutable_scope(summary: EvidenceSummary, baseline: dict, assumptions: dict,
                     source_hashes: dict) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "baselineDataVersion": BASELINE_VERSION,
        "sourceHashes": source_hashes,
        "implementationHashes": implementation_hashes(),
        "assumptions": assumptions,
        "evidence": [{
            "id": r.id, "page": r.page, "quote": r.quote, "sourceQuote": r.source_quote,
            "sourceSpan": r.source_span, "bbox": r.locator_bbox,
            "field": r.extracted_field.value, "typedValue": r.extracted_value,
            "unit": r.unit, "matchMethod": r.match_method, "score": r.match_score,
            "sourceSha256": r.source_sha256,
        } for r in summary.records],
        "uiEvidenceIds": [e["id"] for e in baseline["evidence"]],
    }


def review_template(summary: EvidenceSummary, baseline: dict, assumptions: dict,
                    source_hashes: dict) -> dict:
    scope = _immutable_scope(summary, baseline, assumptions, source_hashes)
    return {
        "kind": "CAUSORA_SYNTHETIC_DEMO_FIELD_REVIEW_V1",
        "scopeSha256": digest(scope),
        "sourceHashes": source_hashes,
        "implementationHashes": scope["implementationHashes"],
        "reviewerName": "",
        "reviewedAtUtc": "",
        "acknowledgement": "",
        "evidence": [{
            "id": r.id, "page": r.page, "quote": r.quote,
            "field": r.extracted_field.value,
            "expectedValue": front_value(r) if r.id in FRONT_IDS else "conditional auto-renew clause present",
            "decision": "pending", "confirmedValue": None, "notes": "",
        } for r in summary.records],
        "assumptions": [{
            "key": key, "expectedValue": assumptions[key],
            "source": "public/demo/supplier_correspondence_log.csv" if key == "noticeSent" else
                      "public/demo/supplier_a_agreement.pdf p.4 + frozen mock" if key in ("forecastBasis", "lockedForecastUnits24m") else
                      "frozen synthetic contract input (not inferred from PDF)",
            "decision": "pending", "confirmedValue": None, "notes": "",
        } for key in ASSUMPTION_KEYS],
    }


def _check_review(review: dict, template: dict) -> None:
    if set(review) != set(template):
        raise ValueError("Review has missing or unknown top-level fields")
    for key in ("kind", "scopeSha256", "sourceHashes", "implementationHashes"):
        if review[key] != template[key]:
            raise ValueError(f"Review is not bound to current {key}")
    name = review["reviewerName"]
    if not isinstance(name, str) or len(name.strip()) < 3 or name.strip().lower() in {"test", "demo", "pending", "reviewer", "unknown"}:
        raise ValueError("An identified, actual human reviewer is required")
    if review["acknowledgement"] != ACK:
        raise ValueError("Reviewer must acknowledge the synthetic-only scope")
    stamp = review["reviewedAtUtc"]
    if not isinstance(stamp, str) or not stamp.endswith("Z"):
        raise ValueError("reviewedAtUtc must be a UTC ISO timestamp ending in Z")
    try:
        at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid reviewer timestamp") from exc
    if at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError("Future-dated review is not accepted")
    for group, ident in (("evidence", "id"), ("assumptions", "key")):
        actuals, expected = review[group], template[group]
        if not isinstance(actuals, list) or len(actuals) != len(expected):
            raise ValueError(f"{group}: incomplete review")
        if [row.get(ident) for row in actuals if isinstance(row, dict)] != [row[ident] for row in expected]:
            raise ValueError(f"{group}: reordered, duplicate or missing IDs")
        for row, frozen in zip(actuals, expected):
            if not isinstance(row, dict) or set(row) != set(frozen):
                raise ValueError(f"{group}: unexpected review fields")
            for key in frozen.keys() - {"decision", "confirmedValue", "notes"}:
                if row[key] != frozen[key]:
                    raise ValueError(f"{row[ident]}: changed immutable quote/source/value")
            if row["decision"] != "approved" or type(row["confirmedValue"]) is not type(frozen["expectedValue"]) or row["confirmedValue"] != frozen["expectedValue"]:
                raise ValueError(f"{row[ident]}: pending, rejected or incorrect confirmation")
            if not isinstance(row["notes"], str):
                raise ValueError(f"{row[ident]}: notes must be text")


def promote(root: Path, review: dict) -> dict[str, dict]:
    """Fail closed until every PDF claim AND explicit synthetic assumption is reviewed."""
    summary, baseline, assumptions, source_hashes = prepare(root)
    template = review_template(summary, baseline, assumptions, source_hashes)
    _check_review(review, template)
    checked = summary.model_copy(deep=True)
    for rec in checked.records:
        rec.manually_verified = True
    variables: list[InternalBusinessVariable] = []
    for rec in checked.records:
        value = rec.extracted_value
        unit = rec.unit
        if rec.extracted_field == EvidenceField.renewal_price_increase_pct:
            value, unit = rec.extracted_value / 100.0, "fraction"
        variables.append(InternalBusinessVariable(name=rec.extracted_field, value=value, unit=unit,
            evidence_id=rec.id, quote_matched=True, manually_verified=True))
    checked.business_variables = variables
    # Keep the source labelled synthetic; LIVE_VERIFIED could be misread as a
    # real-world or live-production contract despite a human checking the fixture.
    checked.status = "MOCK_QUOTE_MATCHED_SYNTHETIC"
    checked = EvidenceSummary.model_validate(checked.model_dump(mode="json"))
    verify_source(checked, root / "public/demo/supplier_a_agreement.pdf")
    by_id = {r.id: r for r in checked.records}
    c = baseline["contract"]
    derived_notice_deadline = date.fromisoformat(assumptions["renewalDate"]) - timedelta(days=by_id["EV-014"].extracted_value)
    contract = {
        "decisionDate": assumptions["decisionDate"], "renewalDate": assumptions["renewalDate"],
        "daysToRenewal": (date.fromisoformat(assumptions["renewalDate"]) - date.fromisoformat(assumptions["decisionDate"])).days,
        "renewalNoticeDays": by_id["EV-014"].extracted_value,
        "noticeDeadline": derived_notice_deadline.isoformat(),
        "noticeSent": assumptions["noticeSent"], "noticeRecordSource": c["noticeRecordSource"],
        "renewalLocked": date.fromisoformat(assumptions["decisionDate"]) > derived_notice_deadline
                         and not assumptions["noticeSent"],
        "renewalTermMonths": by_id["EV-019"].extracted_value,
        "renewalPriceIncreasePct": float(by_id["EV-021"].extracted_value / 100),
        "minPurchaseShareA": float(by_id["EV-024"].extracted_value),
        "forecastBasis": assumptions["forecastBasis"],
        "lockedForecastUnits24m": assumptions["lockedForecastUnits24m"],
        "minPurchaseUnitsA": round(assumptions["lockedForecastUnits24m"] * by_id["EV-024"].extracted_value),
        "terminationFeeUsd": by_id["EV-027"].extracted_value,
        "evidenceIds": list(FRONT_IDS),
    }
    validated_contract = ContractConstraint.model_validate_json(json.dumps(contract))
    if validated_contract.model_dump(mode="json") != contract or contract != c:
        raise ValueError("Derived, reviewed contract disagrees with frozen frontend/engine inputs")
    evidence = []
    for evidence_id in FRONT_IDS:
        rec = by_id[evidence_id]
        evidence.append({"id": evidence_id, "sourceFile": rec.source_file, "page": rec.page,
            "quote": rec.quote, "locatorBbox": rec.locator_bbox,
            "extractedField": rec.extracted_field.value, "extractedValue": front_value(rec),
            "matchMethod": rec.match_method, "matchScore": rec.match_score / 100,
            "quoteMatched": rec.quote_matched})
    # Compute the FIVE exact front-end variable keys, not a sixth unagreed DTO.
    # EV-020 stays as typed internal auto-renew clause evidence, conditional on notice.
    base_variables = {v["key"]: v for v in baseline["variables"]}
    inputs = {
        "renewal_locked": [
            ("decision_date", contract["decisionDate"], "contract.decisionDate"),
            ("renewal_date", contract["renewalDate"], "contract.renewalDate"),
            ("days_to_renewal", f'{contract["daysToRenewal"]} days', "derived"),
            ("renewal_notice_days", f'{contract["renewalNoticeDays"]} days', "EV-014"),
            ("notice_sent_before_deadline", "Yes" if contract["noticeSent"] else "No", "contract.noticeRecordSource"),
        ],
        "renewal_term_months": [("renewal_term_months", str(contract["renewalTermMonths"]), "EV-019"),
                                ("simulation_weeks", "104", "simulation.weeks (target horizon; not computed here)")],
        "effective_price_A": [("base_price_A", f'${baseline["simulation"]["unitPricesUsd"]["A"]:.2f}', "supplier_delivery_history.xlsx (synthetic Day1 input)"),
                              ("renewal_price_increase_pct", f'{by_id["EV-021"].extracted_value:g}%', "EV-021")],
        "min_purchase_share_A": [("min_purchase_share_A", f'{100 * contract["minPurchaseShareA"]:g}%', "EV-024"),
                                 ("forecast_basis", "locked at renewal", "contract.forecastBasis"),
                                 ("locked_forecast_units_24m", f'{contract["lockedForecastUnits24m"]:,} units',
                                  "synthetic renewal-cycle forecast assumption; supplier_a_agreement.pdf p. 4 (not a sum of historical demand)")],
        "termination_fee": [("termination_fee", f'${contract["terminationFeeUsd"]:,}', "EV-027"),
                            ("renewal_locked", "Yes" if contract["renewalLocked"] else "No", "variables.renewal_locked")],
    }
    display = {
        "renewal_locked": ("Yes" if contract["renewalLocked"] else "No", "boolean", "EV-014"),
        "renewal_term_months": (f'{contract["renewalTermMonths"]} months', "months", "EV-019"),
        "effective_price_A": (f'Base × {1 + contract["renewalPriceIncreasePct"]:.2f}', "USD per unit", "EV-021"),
        "min_purchase_share_A": (f'{100 * contract["minPurchaseShareA"]:g}% of locked forecast', "share", "EV-024"),
        "termination_fee": (f'${contract["terminationFeeUsd"]:,}', "USD", "EV-027"),
    }
    if set(base_variables) != set(display) or any(
        base_variables[key]["source"] != source or base_variables[key]["value"] != value or base_variables[key]["unit"] != unit
        for key, (value, unit, source) in display.items()
    ):
        raise ValueError("Generated BusinessVariables differ from the signed v4.1 frontend baseline")
    mapped = [{"key": key, "name": base_variables[key]["name"], "value": display[key][0], "unit": display[key][1],
               "source": display[key][2], "meaning": base_variables[key]["meaning"],
               "inputs": [{"name": name, "value": value, "source": source} for name, value, source in inputs[key]]}
              for key in ("renewal_locked", "renewal_term_months", "effective_price_A", "min_purchase_share_A", "termination_fee")]
    receipt = {
        "kind": "CAUSORA_SYNTHETIC_DEMO_REVIEW_RECEIPT_NOT_REAL_CONTRACT_VERIFICATION",
        "reviewerName": review["reviewerName"].strip(), "reviewedAtUtc": review["reviewedAtUtc"],
        "scopeSha256": template["scopeSha256"], "reviewSha256": digest(review),
        "sourceHashes": source_hashes, "approvedEvidenceIds": [r.id for r in checked.records],
        "approvedAssumptionKeys": list(ASSUMPTION_KEYS),
        "baselineDataVersion": BASELINE_VERSION,
        "humanReviewClaim": "Self-attested review of individual synthetic demo fields/assumptions; identity NOT authenticated",
        "backendState": "NOT CONNECTED", "simulationState": "NOT COMPUTED",
        "implementationHashes": template["implementationHashes"],
    }
    reviewed_version = BASELINE_VERSION + "-wang-day2-reviewed-" + digest(receipt)[:12]
    request_id = "req-wang-day2-" + digest(review)[:12]
    data = {"datasetId": "ds-001", "preprocessStatus": "ready", "dataVersion": reviewed_version,
            "intake": baseline["intake"], "evidence": evidence, "contract": contract, "variables": mapped}
    dataset = {"schemaVersion": SCHEMA_VERSION, "dataVersion": reviewed_version,
               "requestId": request_id, "data": data}
    try:
        DatasetSuccess.model_validate_json(json.dumps(dataset, ensure_ascii=False))
    except ValidationError as exc:
        raise ValueError("DatasetSuccess is incompatible with Jinzhu/Ding v1 wire type") from exc
    validate_promoted_graph(dataset, checked)
    evidence_responses = {entry["id"]: {"schemaVersion": SCHEMA_VERSION,
        "dataVersion": reviewed_version, "requestId": request_id,
        "data": {"evidence": entry}} for entry in evidence}
    for item in evidence_responses.values():
        EvidenceSuccess.model_validate_json(json.dumps(item, ensure_ascii=False))
    internal_handoff = {"kind": "CAUSORA_WANG_TO_JINZHU_SYNTHETIC_CONTRACT_V1",
        "handoffVersion": "wang.evidence_day2.v1", "schemaVersion": SCHEMA_VERSION,
        "datasetId": "ds-001", "dataVersion": reviewed_version,
        "contract": contract,
        # The conditional auto-renew clause EV-020 stays in the ledger; only
        # ContractConstraint.renewalLocked is the activation signal to Jinzhu.
        "businessVariables": [x.model_dump(mode="json") for x in variables if x.evidence_id in FRONT_IDS],
        "sourceHashes": source_hashes, "reviewSha256": digest(review),
        "status": "SELF_ATTESTED_SYNTHETIC_ONLY_NOT_SIMULATED"}
    JinzhuContractHandoff.model_validate_json(json.dumps(internal_handoff, ensure_ascii=False))
    return {"reviewedEvidenceSummary": checked.model_dump(mode="json"), "datasetSuccess": dataset,
            "evidenceSuccessById": evidence_responses,
            "jinzhuContractInput": internal_handoff, "reviewReceipt": receipt,
            "approvedReview": copy.deepcopy(review),
            "reviewScope": _immutable_scope(summary, baseline, assumptions, source_hashes)}
