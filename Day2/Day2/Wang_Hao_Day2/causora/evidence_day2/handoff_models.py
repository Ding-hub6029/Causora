"""Versioned INTERNAL Wang->Jinzhu handoff; NOT an extra public v1 API DTO."""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from causora_day1.adapter import FRONT_IDS, front_value
from causora_day1.schemas import BusinessVariable as InternalVariable
from causora_day1.schemas import EvidenceSummary
from simulation_day1.source_models import Sha256
from simulation_day1.wire_models import ContractConstraint, DatasetSuccess


class Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


CLAIM_TO_FIELD = {
    "EV-014": "renewal_notice_days", "EV-019": "renewal_term_months",
    "EV-021": "renewal_price_increase_pct", "EV-024": "min_purchase_share_A",
    "EV-027": "termination_fee",
}
KEYS = ("renewal_locked", "renewal_term_months", "effective_price_A",
        "min_purchase_share_A", "termination_fee")


class JinzhuContractHandoff(Strict):
    kind: Literal["CAUSORA_WANG_TO_JINZHU_SYNTHETIC_CONTRACT_V1"]
    handoffVersion: Literal["wang.evidence_day2.v1"]
    schemaVersion: Literal["causora.contract.v1"]
    datasetId: Literal["ds-001"]
    dataVersion: str = Field(pattern=r"^demo-2026\.10\.04-v4-wang-day2-reviewed-[a-f0-9]{12}$")
    contract: ContractConstraint
    businessVariables: list[InternalVariable] = Field(min_length=5, max_length=5)
    sourceHashes: dict[str, Sha256]
    reviewSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["SELF_ATTESTED_SYNTHETIC_ONLY_NOT_SIMULATED"]

    @model_validator(mode="after")
    def semantic_links(self):
        by_id = {variable.evidence_id: variable for variable in self.businessVariables}
        if len(by_id) != 5 or set(by_id) != set(FRONT_IDS):
            raise ValueError("Jinzhu handoff must have one variable per public evidence ID; EV-020 remains ledger-only")
        if self.contract.evidenceIds != list(FRONT_IDS):
            raise ValueError("Handoff contract must cite precisely the five public evidence IDs")
        if any(by_id[eid].name.value != CLAIM_TO_FIELD[eid] for eid in FRONT_IDS):
            raise ValueError("Handoff variable/claim mapping changed")
        if (by_id["EV-014"].value != self.contract.renewalNoticeDays or
                by_id["EV-019"].value != self.contract.renewalTermMonths or
                by_id["EV-021"].value != self.contract.renewalPriceIncreasePct or
                by_id["EV-024"].value != self.contract.minPurchaseShareA or
                by_id["EV-027"].value != self.contract.terminationFeeUsd):
            raise ValueError("Handoff variable values must equal reviewed ContractConstraint")
        if any(not x.manually_verified or not x.quote_matched for x in self.businessVariables):
            raise ValueError("Handoff cannot promote a pending clause")
        required = ("public/demo/supplier_a_agreement.pdf", "public/demo/supplier_correspondence_log.csv",
                    "demo_data/causora_day1_mock.json")
        if any(len(self.sourceHashes.get(key, "")) != 64 for key in required):
            raise ValueError("Missing hash-bound synthetic source")
        return self


def validate_promoted_graph(payload: dict, ledger: EvidenceSummary) -> None:
    """Relational checks absent from the shared v1 wire schema (which is kept unchanged).

    Consumer must also check the separate bundle manifest and original PDF digest.
    This does not authenticate the reviewer and does not validate a real supplier.
    """
    # Strict Pydantic dates and tuple locators are decoded from the *wire JSON*,
    # not from a Python dict whose values are still strings and lists.
    parsed = DatasetSuccess.model_validate_json(json.dumps(payload, ensure_ascii=False))
    data = parsed.data
    if data.contract.evidenceIds != list(FRONT_IDS) or len(data.evidence) != 5 or len(data.variables) != 5:
        raise ValueError("Dataset graph missing/duplicate public evidence or variables")
    ids = [e.id for e in data.evidence]
    if ids != list(FRONT_IDS):
        raise ValueError("Dataset evidence order, uniqueness or ID set changed")
    if [v.key for v in data.variables] != list(KEYS):
        raise ValueError("Dataset BusinessVariable keys/order changed")
    if [v.source for v in data.variables] != list(FRONT_IDS):
        raise ValueError("Dataset variable/evidence links changed")
    by_id = {rec.id: rec for rec in ledger.records}
    if len(by_id) != 6 or set(by_id) != set(FRONT_IDS) | {"EV-020"}:
        raise ValueError("Internal source ledger missing or duplicating evidence")
    for item in data.evidence:
        rec = by_id[item.id]
        if (not rec.manually_verified or not rec.quote_matched or
                item.quote != rec.quote or item.page != rec.page or
                item.sourceFile != rec.source_file or item.locatorBbox != tuple(rec.locator_bbox) or
                item.extractedField != rec.extracted_field.value or
                item.extractedValue != front_value(rec) or item.matchScore != rec.match_score / 100 or
                item.matchMethod != rec.match_method or not item.quoteMatched):
            raise ValueError(f"{item.id}: wire Evidence disagrees with reviewed PDF ledger")
    contract = data.contract
    if (contract.renewalNoticeDays != by_id["EV-014"].extracted_value or
            contract.renewalTermMonths != by_id["EV-019"].extracted_value or
            contract.renewalPriceIncreasePct != by_id["EV-021"].extracted_value / 100 or
            contract.minPurchaseShareA != by_id["EV-024"].extracted_value or
            contract.terminationFeeUsd != by_id["EV-027"].extracted_value):
        raise ValueError("ContractConstraint is not sourced from the reviewed PDF")
    expected = (
        ("Yes" if contract.renewalLocked else "No", "boolean"),
        (f"{contract.renewalTermMonths} months", "months"),
        (f"Base × {1 + contract.renewalPriceIncreasePct:.2f}", "USD per unit"),
        (f"{100 * contract.minPurchaseShareA:g}% of locked forecast", "share"),
        (f"${contract.terminationFeeUsd:,}", "USD"),
    )
    for var, (value, unit) in zip(data.variables, expected):
        if (var.value, var.unit) != (value, unit):
            raise ValueError(f"{var.key}: display value/unit not derived from reviewed contract")
        for inp in var.inputs:
            if inp.source.startswith("EV-") and inp.source not in by_id:
                raise ValueError(f"{var.key}: orphan input evidence reference")
    if data.dataVersion != parsed.dataVersion:
        raise ValueError("Dataset envelope and payload dataVersion disagree")
