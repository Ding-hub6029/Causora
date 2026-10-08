"""Strict, self-contained Python wire models for the frozen Causora v1 contract.

This module deliberately mirrors only the fields Day 3 consumes.  It does not
modify ``reference/contracts.ts`` and imports neither a simulator nor an
old evidence-preparation package.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "causora.contract.v1"
OptionId = Literal["D0", "D1", "D2"]
Role = Literal["CFO", "COO", "Risk"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIMESTAMP = re.compile(r"^.+Z$")
_FROZEN_SOURCE_MANIFEST_SHA256 = "14f4fd2748f74dbf16ad3bade6df2d372a8a244e171488138a44fbda7acfc92e"


def _reject_non_finite(value: Any) -> None:
    """Reject NaN/Infinity anywhere in a JSON-shaped value before coercion."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Numbers must be finite")
    elif isinstance(value, dict):
        for child in value.values():
            _reject_non_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_non_finite(child)


def canonical_json(value: Any) -> bytes:
    """Stable semantic JSON: a TS number spelled 0 or 0.0 hashes identically.

    Internal sidecar protocol, not RFC 8785: keys sorted, UTF-8, no whitespace,
    finite floats with whole values converted to integers before JSON encoding.
    """
    def numbers(item: Any) -> Any:
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("Numbers must be finite")
            return int(item) if item.is_integer() else item
        if isinstance(item, dict):
            return {key: numbers(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [numbers(child) for child in item]
        return item
    return json.dumps(numbers(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    def bad_constant(token: str) -> None:
        raise ValueError(f"Non-finite JSON token is forbidden: {token}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=bad_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object")
    _reject_non_finite(value)
    return value


class StrictModel(BaseModel):
    """No implicit coercion, unknown fields, NaN/Infinity, or attribute replacement."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, revalidate_instances="always")

    @field_validator("*", mode="before")
    @classmethod
    def finite_json_numbers(cls, value: Any) -> Any:
        _reject_non_finite(value)
        return value


class Scenario(StrictModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    demandShock: float
    demandUnits24m: int = Field(ge=0)
    leadTime: str = Field(min_length=1)
    leadTimeMultiplier: float = Field(gt=0)
    description: str = Field(min_length=1)


class DecisionOption(StrictModel):
    id: OptionId
    label: str = Field(min_length=1)
    shareA: float = Field(ge=0, le=1)
    terminateA: bool
    allocation: str = Field(min_length=1)
    short: str = Field(min_length=1)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def fixed_option_meaning(self) -> "DecisionOption":
        share, terminate = {"D0": (1.0, False), "D1": (0.6, False), "D2": (0.0, True)}[self.id]
        if self.shareA != share or self.terminateA is not terminate:
            raise ValueError("D0/D1/D2 retain the shared contract's fixed allocation and exit meaning")
        return self


class EvidenceRecord(StrictModel):
    id: str = Field(pattern=r"^EV-\d{3}$")
    sourceFile: str = Field(min_length=1)
    page: int = Field(ge=1)
    quote: str = Field(min_length=1)
    locatorBbox: tuple[float, float, float, float] | None
    extractedField: str = Field(min_length=1)
    extractedValue: str = Field(min_length=1)
    matchMethod: Literal["exact", "fuzzy"]
    matchScore: float = Field(ge=0, le=1)
    quoteMatched: bool

    @field_validator("locatorBbox", mode="before")
    @classmethod
    def json_bbox_array_to_tuple(cls, value: Any) -> Any:
        # JSON has arrays rather than tuples; retain a tuple internally after this
        # explicit wire decode instead of weakening strict validation globally.
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def valid_bbox(self) -> "EvidenceRecord":
        if self.locatorBbox is not None:
            x0, y0, x1, y1 = self.locatorBbox
            if min(x0, y0, x1, y1) < 0 or x1 <= x0 or y1 <= y0:
                raise ValueError("locatorBbox must be [x0,y0,x1,y1] with non-negative increasing coordinates")
        return self


class ContractConstraint(StrictModel):
    decisionDate: str
    renewalDate: str
    daysToRenewal: int = Field(ge=0)
    renewalNoticeDays: int = Field(ge=0)
    noticeDeadline: str
    noticeSent: bool
    noticeRecordSource: str = Field(min_length=1)
    renewalLocked: bool
    renewalTermMonths: int = Field(gt=0)
    renewalPriceIncreasePct: float = Field(ge=0)
    minPurchaseShareA: float = Field(ge=0, le=1)
    forecastBasis: Literal["locked-at-renewal", "rolling"]
    lockedForecastUnits24m: int = Field(ge=0)
    minPurchaseUnitsA: int = Field(ge=0)
    terminationFeeUsd: int = Field(ge=0)
    evidenceIds: list[str] = Field(min_length=1)

    @field_validator("decisionDate", "renewalDate", "noticeDeadline")
    @classmethod
    def iso_calendar_date(cls, value: str) -> str:
        if not _DATE.fullmatch(value):
            raise ValueError("Dates must use YYYY-MM-DD")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Invalid calendar date") from exc
        return value

    @model_validator(mode="after")
    def exact_contract_dates_and_ids(self) -> "ContractConstraint":
        decision = date.fromisoformat(self.decisionDate)
        renewal = date.fromisoformat(self.renewalDate)
        deadline = date.fromisoformat(self.noticeDeadline)
        if (renewal - decision).days != self.daysToRenewal:
            raise ValueError("daysToRenewal must equal renewalDate - decisionDate")
        if (renewal - deadline).days != self.renewalNoticeDays:
            raise ValueError("noticeDeadline must equal renewalDate - renewalNoticeDays")
        if self.renewalLocked is not (decision > deadline and not self.noticeSent):
            raise ValueError("renewalLocked must follow the configured dates and timely-notice condition")
        if len(self.evidenceIds) != len(set(self.evidenceIds)):
            raise ValueError("Contract evidence IDs must be unique")
        # The absolute purchase floor is a whole-unit contract field, not a rounded display claim.
        if abs(self.lockedForecastUnits24m * self.minPurchaseShareA - self.minPurchaseUnitsA) > 1e-9:
            raise ValueError("minPurchaseUnitsA must exactly equal locked forecast × minimum share")
        return self


class BusinessVariableInput(StrictModel):
    name: str = Field(min_length=1)
    value: str
    source: str = Field(min_length=1)


class BusinessVariable(StrictModel):
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    value: str
    unit: str = Field(min_length=1)
    source: str = Field(min_length=1)
    meaning: str = Field(min_length=1)
    inputs: list[BusinessVariableInput]


class CostBreakdown(StrictModel):
    purchase: int
    holding: int
    stockoutLoss: int
    renewalPremium: int
    terminationFee: int


class MetricCell(StrictModel):
    optionId: OptionId
    feasible: bool
    expectedTco: int
    stockoutProbability: float = Field(ge=0, le=1)
    serviceLevel: float = Field(ge=0, le=1)
    cashOutflowP90: int
    breakdown: CostBreakdown
    unitsFromA: int = Field(ge=0)
    unitsFromB: int = Field(ge=0)
    tone: Literal["neutral", "recommended", "risk"]

    @model_validator(mode="after")
    def exact_tco_and_nonempty_procurement(self) -> "MetricCell":
        if self.expectedTco != sum((self.breakdown.purchase, self.breakdown.holding,
                                    self.breakdown.stockoutLoss, self.breakdown.renewalPremium,
                                    self.breakdown.terminationFee)):
            raise ValueError("expectedTco must equal the exact integer sum of breakdown fields")
        if self.unitsFromA + self.unitsFromB <= 0:
            raise ValueError("A metric cell must state a non-zero procurement total")
        return self


class UnitPricesUsd(StrictModel):
    A: float = Field(ge=0)
    B: float = Field(ge=0)


class SimulationResult(StrictModel):
    simulationId: str = Field(min_length=1)
    seed: int = Field(ge=0)
    dataVersion: str = Field(min_length=1)
    formulaVersion: str = Field(min_length=1)
    weeks: int = Field(gt=0)
    monteCarloRuns: int = Field(ge=0)
    unitPricesUsd: UnitPricesUsd
    matrix: dict[str, list[MetricCell]] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_nonempty_cells(self) -> "SimulationResult":
        for scenario_id, cells in self.matrix.items():
            if not scenario_id or not cells:
                raise ValueError("Every matrix scenario must have a non-empty ID and cells")
            ids = [cell.optionId for cell in cells]
            if len(ids) != len(set(ids)):
                raise ValueError("Each scenario must have unique option cells")
            if set(ids) != {"D0", "D1", "D2"}:
                raise ValueError("Each scenario must include all three shared decision options")
        return self


class ConstraintViolation(StrictModel):
    optionId: OptionId
    code: Literal["infeasible", "stockout_threshold", "cash_ceiling"]


class SelectedScenarioSelection(StrictModel):
    scenarioId: str = Field(min_length=1)
    status: Literal["selected"]
    recommendedOptionId: OptionId
    constraintViolations: list[ConstraintViolation]


class NoFeasibleScenarioSelection(StrictModel):
    scenarioId: str = Field(min_length=1)
    status: Literal["no_feasible_option"]
    recommendedOptionId: None
    constraintViolations: list[ConstraintViolation]


ScenarioSelection = SelectedScenarioSelection | NoFeasibleScenarioSelection


class SelectionLimits(StrictModel):
    riskThreshold: float = Field(ge=0, le=1)
    budgetCeilingUsd: int = Field(ge=0)


class RealSimulationReference(StrictModel):
    """Reference supplied by the simulation owner, not generated by Day 3."""

    schemaVersion: Literal[SCHEMA_VERSION]
    dataVersion: str = Field(min_length=1)
    datasetId: str = Field(min_length=1)
    simulationId: str = Field(min_length=1)
    scenarioId: str = Field(min_length=1)
    optionIds: list[OptionId] = Field(min_length=3, max_length=3)
    simulationSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshotSha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def ordered_options(self) -> "RealSimulationReference":
        if self.optionIds != ["D0", "D1", "D2"]:
            raise ValueError("Simulation reference must bind frozen ordered D0/D1/D2")
        return self


class BoardroomSnapshot(StrictModel):
    """Internal Day 3 input; never a public BoardroomResponse DTO."""

    sourceMode: Literal["LOCAL_MOCK", "SIMULATION_READY"]
    schemaVersion: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    scenario: Scenario
    options: list[DecisionOption] = Field(min_length=3, max_length=3)
    simulation: SimulationResult
    contract: ContractConstraint
    evidence: list[EvidenceRecord] = Field(min_length=1)
    selection: ScenarioSelection | None = None
    selectionLimits: SelectionLimits | None = None
    simulationReference: RealSimulationReference | None = None

    @model_validator(mode="after")
    def coherent_cross_module_values(self) -> "BoardroomSnapshot":
        option_ids = [option.id for option in self.options]
        if option_ids != ["D0", "D1", "D2"]:
            raise ValueError("Options must be exactly ordered D0/D1/D2")
        if self.scenario.id not in self.simulation.matrix:
            raise ValueError("Scenario has no simulation matrix")
        cells = self.simulation.matrix[self.scenario.id]
        if [cell.optionId for cell in cells] != option_ids:
            raise ValueError("Scenario cells must exactly bind the ordered option list")
        if [evidence.id for evidence in self.evidence] != self.contract.evidenceIds:
            raise ValueError("Evidence records must match the ordered contract evidence IDs")
        if len({evidence.id for evidence in self.evidence}) != len(self.evidence):
            raise ValueError("Evidence IDs must be unique")
        by_option = {option.id: option for option in self.options}
        for cell in cells:
            option = by_option[cell.optionId]
            total = cell.unitsFromA + cell.unitsFromB
            if abs(cell.unitsFromA / total - option.shareA) > 1e-12:
                raise ValueError("Cell A/B units must exactly bind the referenced option shareA")
            if option.terminateA and cell.unitsFromA != 0:
                raise ValueError("A terminating option cannot procure units from A")
        if self.sourceMode == "LOCAL_MOCK":
            if self.selection is not None or self.selectionLimits is not None or self.simulationReference is not None:
                raise ValueError("LOCAL_MOCK cannot claim an authenticated selection or simulation reference")
        else:
            if self.selection is None or self.selectionLimits is None or self.simulationReference is None:
                raise ValueError("SIMULATION_READY requires selection limits and a simulation-owner reference")
            self._validate_real_reference_and_selection(cells)
        return self

    def _validate_real_reference_and_selection(self, cells: list[MetricCell]) -> None:
        assert self.selection is not None and self.selectionLimits is not None and self.simulationReference is not None
        ref = self.simulationReference
        if (ref.dataVersion != self.simulation.dataVersion or ref.simulationId != self.simulation.simulationId or
                ref.scenarioId != self.scenario.id or ref.optionIds != [option.id for option in self.options]):
            raise ValueError("Simulation reference must bind this exact dataVersion, simulation ID, scenario, and options")
        if ref.simulationSha256 != sha256_json(self.simulation.model_dump(mode="json")):
            raise ValueError("Simulation result no longer matches the simulation-owner hash")
        hash_payload = {
            "schemaVersion": self.schemaVersion, "dataVersion": self.simulation.dataVersion,
            "scenario": self.scenario.model_dump(mode="json"),
            "options": [item.model_dump(mode="json") for item in self.options],
            "simulation": self.simulation.model_dump(mode="json"),
            "contract": self.contract.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in self.evidence],
            "selection": self.selection.model_dump(mode="json"),
            "selectionLimits": self.selectionLimits.model_dump(mode="json"),
        }
        if ref.snapshotSha256 != sha256_json(hash_payload):
            raise ValueError("Direct snapshot no longer matches the simulation-owner full-input hash")
        if self.selection.scenarioId != self.scenario.id:
            raise ValueError("Selection belongs to another scenario")
        expected_violations: list[tuple[OptionId, str]] = []
        eligible: list[MetricCell] = []
        for cell in cells:
            if not cell.feasible:
                expected_violations.append((cell.optionId, "infeasible"))
            if cell.stockoutProbability > self.selectionLimits.riskThreshold:
                expected_violations.append((cell.optionId, "stockout_threshold"))
            if cell.cashOutflowP90 > self.selectionLimits.budgetCeilingUsd:
                expected_violations.append((cell.optionId, "cash_ceiling"))
            if (cell.feasible and cell.stockoutProbability <= self.selectionLimits.riskThreshold and
                    cell.cashOutflowP90 <= self.selectionLimits.budgetCeilingUsd):
                eligible.append(cell)
        actual_violations = [(item.optionId, item.code) for item in self.selection.constraintViolations]
        if actual_violations != expected_violations:
            raise ValueError("Selection constraint violations must be complete and deterministically ordered")
        if isinstance(self.selection, SelectedScenarioSelection):
            if not eligible:
                raise ValueError("A selected result cannot exist when no option is eligible")
            winner = min(eligible, key=lambda cell: (cell.expectedTco, cell.optionId)).optionId
            if self.selection.recommendedOptionId != winner:
                raise ValueError("Selected option must be the eligible deterministic TCO winner")
        elif eligible:
            raise ValueError("no_feasible_option is invalid while an eligible option exists")


class IntakeFile(StrictModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: str = Field(min_length=1)
    detail: str
    size: str = Field(min_length=1)
    status: str = Field(min_length=1)
    icon: str = Field(min_length=1)
    path: str = Field(min_length=1)


class DatasetResult(StrictModel):
    datasetId: str = Field(min_length=1)
    preprocessStatus: Literal["ready"]
    dataVersion: str = Field(min_length=1)
    intake: list[IntakeFile]
    evidence: list[EvidenceRecord] = Field(min_length=1)
    contract: ContractConstraint
    variables: list[BusinessVariable]

    @model_validator(mode="after")
    def dataset_graph(self) -> "DatasetResult":
        if self.dataVersion == "":
            raise ValueError("Dataset dataVersion is required")
        if [item.id for item in self.evidence] != self.contract.evidenceIds:
            raise ValueError("Dataset contract and evidence IDs differ")
        if len({item.id for item in self.evidence}) != len(self.evidence):
            raise ValueError("Dataset evidence IDs must be unique")
        if len({item.key for item in self.variables}) != len(self.variables):
            raise ValueError("Dataset variable keys must be unique")
        if any(item.source not in self.contract.evidenceIds for item in self.variables):
            raise ValueError("BusinessVariable source must resolve to a dataset evidence record")
        return self


class DatasetSuccessEnvelope(StrictModel):
    schemaVersion: Literal[SCHEMA_VERSION]
    dataVersion: str = Field(min_length=1)
    requestId: str = Field(min_length=1)
    data: DatasetResult

    @model_validator(mode="after")
    def consistent_data_version(self) -> "DatasetSuccessEnvelope":
        if self.dataVersion != self.data.dataVersion:
            raise ValueError("Dataset envelope and data dataVersion differ")
        return self


class ReviewScope(StrictModel):
    """Sidecar scope for a manually signed/recorded review bundle (internal gate)."""

    kind: Literal["CAUSORA_EVIDENCE_REVIEW_SCOPE_V1"]
    schemaVersion: Literal[SCHEMA_VERSION]
    dataVersion: str = Field(min_length=1)
    datasetSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sourceHashes: dict[str, str] = Field(min_length=1)

    @field_validator("sourceHashes")
    @classmethod
    def source_hashes_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not path or not _SHA256.fullmatch(digest) for path, digest in value.items()):
            raise ValueError("Every review source hash must be a SHA-256 digest")
        return value


class HumanReceipt(StrictModel):
    """Read-only proof-of-review receipt. It is not an HTTP contract field."""

    kind: Literal["CAUSORA_HUMAN_REVIEW_RECEIPT_V1"]
    reviewerType: Literal["human"]
    reviewerName: str = Field(min_length=3)
    reviewedAtUtc: str
    scopeSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    datasetSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sourceHashes: dict[str, str] = Field(min_length=1)
    allApproved: Literal[True]
    approvedEvidenceIds: list[str] = Field(min_length=1)
    approvedAssumptionKeys: list[str] = Field(min_length=5, max_length=5)

    @field_validator("reviewedAtUtc")
    @classmethod
    def utc_timestamp(cls, value: str) -> str:
        if not _TIMESTAMP.fullmatch(value):
            raise ValueError("reviewedAtUtc must be an ISO UTC timestamp ending in Z")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("reviewedAtUtc is not a valid ISO timestamp") from exc
        return value

    @field_validator("sourceHashes")
    @classmethod
    def receipt_hashes_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not path or not _SHA256.fullmatch(digest) for path, digest in value.items()):
            raise ValueError("Every receipt source hash must be a SHA-256 digest")
        return value

    @model_validator(mode="after")
    def approvals_are_unique(self) -> "HumanReceipt":
        if len(self.approvedEvidenceIds) != len(set(self.approvedEvidenceIds)):
            raise ValueError("approvedEvidenceIds must be unique")
        if len(self.approvedAssumptionKeys) != len(set(self.approvedAssumptionKeys)):
            raise ValueError("approvedAssumptionKeys must be unique")
        return self


class RealSnapshotInput(StrictModel):
    """Typed, hash-bound external Jinzhu SimulationResult integration payload."""

    schemaVersion: Literal[SCHEMA_VERSION]
    dataVersion: str = Field(min_length=1)
    scenario: Scenario
    options: list[DecisionOption] = Field(min_length=3, max_length=3)
    simulation: SimulationResult
    contract: ContractConstraint
    evidence: list[EvidenceRecord] = Field(min_length=1)
    selection: ScenarioSelection
    selectionLimits: SelectionLimits
    reference: RealSimulationReference

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "dataVersion": self.dataVersion,
            "scenario": self.scenario.model_dump(mode="json"),
            "options": [item.model_dump(mode="json") for item in self.options],
            "simulation": self.simulation.model_dump(mode="json"),
            "contract": self.contract.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in self.evidence],
            "selection": self.selection.model_dump(mode="json"),
            "selectionLimits": self.selectionLimits.model_dump(mode="json"),
        }

    @model_validator(mode="after")
    def reference_binds_all_input(self) -> "RealSnapshotInput":
        if self.dataVersion != self.simulation.dataVersion or self.dataVersion != self.reference.dataVersion:
            raise ValueError("Input, simulation, and reference dataVersion must match")
        if self.reference.simulationId != self.simulation.simulationId:
            raise ValueError("Reference simulation ID does not match SimulationResult")
        if self.reference.simulationSha256 != sha256_json(self.simulation.model_dump(mode="json")):
            raise ValueError("Reference simulation SHA-256 mismatch")
        if self.reference.snapshotSha256 != sha256_json(self._hash_payload()):
            raise ValueError("Reference snapshot SHA-256 mismatch; input may have been modified")
        # Reuse Snapshot's stronger cell/selection and reference validation.
        BoardroomSnapshot(sourceMode="SIMULATION_READY", scenario=self.scenario, options=self.options,
                          simulation=self.simulation, contract=self.contract, evidence=self.evidence,
                          selection=self.selection, selectionLimits=self.selectionLimits,
                          simulationReference=self.reference)
        return self

    def to_boardroom_snapshot(self) -> BoardroomSnapshot:
        return BoardroomSnapshot(sourceMode="SIMULATION_READY", scenario=self.scenario, options=self.options,
                                 simulation=self.simulation, contract=self.contract, evidence=self.evidence,
                                 selection=self.selection, selectionLimits=self.selectionLimits,
                                 simulationReference=self.reference)


class LocalMockMeta(StrictModel):
    schemaVersion: Literal[SCHEMA_VERSION]
    product: str
    version: str
    dataVersion: str
    status: Literal["verified-local-mock"]
    seed: int = Field(ge=0)
    notice: str


def local_fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "causora_day1_mock.json"


def _verify_default_frozen_fixture() -> None:
    """Pin LOCAL_MOCK to the current read-only source-hash manifest."""
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "reference" / "source_hashes.json"
    if not manifest_path.is_file():
        raise ValueError("Frozen source hash manifest is missing")
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != _FROZEN_SOURCE_MANIFEST_SHA256:
        raise ValueError("Frozen source hash manifest changed")
    manifest = read_json_object(manifest_path)
    expected = manifest.get("fixtures/causora_day1_mock.json")
    actual = hashlib.sha256(local_fixture_path().read_bytes()).hexdigest()
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected) or actual != expected:
        raise ValueError("Frozen local mock hash differs from the pinned source manifest")


def load_local_mock_snapshot(scenario_id: str = "demand-drop", path: Path | None = None) -> BoardroomSnapshot:
    """Load the frozen local fixture directly; no ZIP, old project root, or preparer is needed."""
    if path is None:
        _verify_default_frozen_fixture()
    raw = read_json_object(path or local_fixture_path())
    required = {"meta", "scenarios", "options", "simulation", "contract", "evidence"}
    if not required <= set(raw):
        raise ValueError("Frozen local mock is missing required Day 3 material")
    meta = LocalMockMeta.model_validate(raw["meta"])
    scenarios = [Scenario.model_validate(item) for item in raw["scenarios"]]
    options = [DecisionOption.model_validate(item) for item in raw["options"]]
    simulation = SimulationResult.model_validate(raw["simulation"])
    contract = ContractConstraint.model_validate(raw["contract"])
    evidence = [EvidenceRecord.model_validate(item) for item in raw["evidence"]]
    if simulation.dataVersion != meta.dataVersion or simulation.seed != meta.seed:
        raise ValueError("Frozen local mock metadata and simulation disagree")
    try:
        scenario = next(item for item in scenarios if item.id == scenario_id)
    except StopIteration as exc:
        raise ValueError(f"Unknown frozen mock scenario: {scenario_id}") from exc
    return BoardroomSnapshot(sourceMode="LOCAL_MOCK", scenario=scenario, options=options,
                             simulation=simulation, contract=contract, evidence=evidence)


def load_real_snapshot_input(path: Path) -> RealSnapshotInput:
    """Reject unknown/coerced input fields before making the immutable reference check."""
    raw = read_json_object(path)
    typed = RealSnapshotInput.model_validate(raw)
    # Strict schemas should preserve JSON field structure. This explicit equality prevents a
    # future permissive field from silently changing what the simulation-owner hash covered.
    if typed.model_dump(mode="json") != raw:
        raise ValueError("Input changed during parsing; only canonical strict wire JSON is accepted")
    return typed
