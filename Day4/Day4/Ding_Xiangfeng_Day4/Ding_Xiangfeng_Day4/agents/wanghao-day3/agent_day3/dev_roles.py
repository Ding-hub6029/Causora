"""Development-only, code-bound Day 3 role commentary for Jinzhu's deterministic preview.

This module is intentionally separate from the reviewed/public Day 3 path.  It consumes
only a hash-bound, independently audited *unreviewed* deterministic preview and emits an
internal development analysis.  It neither creates a SimulationResult nor modifies any
shared HTTP DTO, review gate, decision, recommendation, Critic, or Brief.

Providers never author prose or numeric claims.  They may select only IDs from a catalog
constructed in this module from narrow typed projections.  Statements, references, and
metric bindings are rendered by code from those projections after selection.
"""
from __future__ import annotations

import asyncio
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol, TypeAlias

from pydantic import Field, field_validator, model_validator

from .wire_models import Role, StrictModel, sha256_json


ROLES: tuple[Role, ...] = ("CFO", "COO", "Risk")
BUNDLE_KIND = "CAUSORA_UNREVIEWED_DEVELOPMENT_BUNDLE_V1"
LINEAGE_KIND = "CAUSORA_UNREVIEWED_DEVELOPMENT_LINEAGE_V1"
TRACE_AUDIT_KIND = "CAUSORA_DAY3_DEV_ONLY_TRACE_AUDIT_V1"
PREVIEW_KIND = "CAUSORA_DAY2_INTERNAL_DETERMINISTIC_PREVIEW_V1"
BASELINE_SOURCE_DATA_VERSION = "demo-2026.10.04-v4"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OPTION_IDS = ("D0", "D1", "D2")
_COST_FIELDS = ("purchase", "holding", "stockoutLoss", "renewalPremium", "terminationFee")
_NUMBER_WORDS = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"single|double|triple|percentile)\b",
    re.IGNORECASE,
)


class DevCfoCostBreakdown(StrictModel):
    """The five audited deterministic TCO components for an option."""

    purchase: int = Field(ge=0)
    holding: int = Field(ge=0)
    stockoutLoss: int = Field(ge=0)
    renewalPremium: int = Field(ge=0)
    terminationFee: int = Field(ge=0)


class DevCfoOption(StrictModel):
    optionId: Literal["D0", "D1", "D2"]
    tcoUsd: int = Field(ge=0)
    cashOutflowUsd: int = Field(ge=0)
    deltaTcoUsdFromD0: int
    costBreakdownUsd: DevCfoCostBreakdown
    revenueUsd: int
    grossProfitUsd: int
    grossMargin: float | None
    grossMarginStatus: Literal["VALID", "INVALID_REVENUE_ZERO"]

    @model_validator(mode="after")
    def tco_reconciles(self) -> "DevCfoOption":
        if self.tcoUsd != sum(getattr(self.costBreakdownUsd, field) for field in _COST_FIELDS):
            raise ValueError("deterministic TCO must equal the five displayed cost components")
        return self


class DevCfoProjection(StrictModel):
    """CFO receives only actual deterministic financial results for one scenario."""

    role: Literal["CFO"] = "CFO"
    scenarioId: str = Field(min_length=1)
    options: list[DevCfoOption] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def ordered_options(self) -> "DevCfoProjection":
        if [item.optionId for item in self.options] != list(_OPTION_IDS):
            raise ValueError("CFO projection must retain D0/D1/D2 ordering")
        if self.options[0].deltaTcoUsdFromD0 != 0:
            raise ValueError("D0 TCO delta must be zero")
        return self


class DevCooOption(StrictModel):
    optionId: Literal["D0", "D1", "D2"]
    orderedUnitsA: int = Field(ge=0)
    orderedUnitsB: int = Field(ge=0)
    deliveredUnitsA: int = Field(ge=0)
    deliveredUnitsB: int = Field(ge=0)
    endingInventoryUnits: int = Field(ge=0)
    unitsInTransitAtEnd: int = Field(ge=0)
    fulfilledUnits: int = Field(ge=0)
    lostUnits: int = Field(ge=0)
    serviceLevel: float = Field(ge=0, le=1)
    stockoutOccurred: bool


class DevCooProjection(StrictModel):
    """COO receives operations only: no contract, financial, trace, or evidence data."""

    role: Literal["COO"] = "COO"
    scenarioId: str = Field(min_length=1)
    demandUnits24m: int = Field(ge=0)
    demandShock: float
    leadTime: str = Field(min_length=1)
    leadTimeMultiplier: float = Field(gt=0)
    options: list[DevCooOption] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def ordered_options(self) -> "DevCooProjection":
        if [item.optionId for item in self.options] != list(_OPTION_IDS):
            raise ValueError("COO projection must retain D0/D1/D2 ordering")
        return self


class DevRiskContract(StrictModel):
    """Clause values only: source files, PDF pages, and quotes are intentionally absent."""

    renewalLocked: bool
    renewalNoticeDays: int = Field(ge=0)
    renewalTermMonths: int = Field(gt=0)
    renewalPriceIncreasePct: float = Field(ge=0)
    minPurchaseShareA: float = Field(ge=0, le=1)
    forecastBasis: Literal["locked-at-renewal", "rolling"]
    lockedForecastUnits24m: int = Field(ge=0)
    minPurchaseUnitsA: int = Field(ge=0)
    terminationFeeUsd: int = Field(ge=0)

    @model_validator(mode="after")
    def fixed_floor_reconciles(self) -> "DevRiskContract":
        if abs(self.lockedForecastUnits24m * self.minPurchaseShareA - self.minPurchaseUnitsA) > 1e-9:
            raise ValueError("risk contract purchase floor must reconcile exactly")
        return self


class DevRiskScenario(StrictModel):
    demandShock: float
    leadTime: str = Field(min_length=1)
    leadTimeMultiplier: float = Field(gt=0)


class DevRiskPolicy(StrictModel):
    """Policy labels relevant to development provenance, without inventory or price inputs."""

    assumptionStatus: Literal["UNAPPROVED_TEST_INPUT"]
    cashTiming: Literal["at_order"]
    purchaseRecognition: Literal["at_order"]
    roundingMode: Literal["half_even"]
    demandMode: Literal["history_rescaled_to_scenario_units"]
    leadTimeMode: Literal["seed_rotated_empirical_cycle"]
    leadStressAppliesTo: Literal["A_only", "all_suppliers"]
    commitmentSchedule: Literal["linear_weekly"]
    holdingBasis: Literal["available_ending_average"]
    deterministicRuns: Literal[1]
    monteCarloRuns: Literal[0]


class DevRiskOption(StrictModel):
    optionId: Literal["D0", "D1", "D2"]
    feasible: bool
    cashOutflowUsd: int = Field(ge=0)
    stockoutOccurred: bool


class DevRiskProjection(StrictModel):
    """Risk gets pending-review status, matched IDs, contract clauses, and limited risks only."""

    role: Literal["Risk"] = "Risk"
    scenarioId: str = Field(min_length=1)
    humanReviewStatus: Literal["pending"]
    decisionReady: Literal[False]
    matchedEvidenceIds: list[str] = Field(min_length=1)
    scenario: DevRiskScenario
    policy: DevRiskPolicy
    contract: DevRiskContract
    options: list[DevRiskOption] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def ordered_options_and_evidence(self) -> "DevRiskProjection":
        if [item.optionId for item in self.options] != list(_OPTION_IDS):
            raise ValueError("Risk projection must retain D0/D1/D2 ordering")
        if len(self.matchedEvidenceIds) != len(set(self.matchedEvidenceIds)):
            raise ValueError("matched evidence IDs must be unique")
        return self


DevProjection: TypeAlias = DevCfoProjection | DevCooProjection | DevRiskProjection
MetricValue: TypeAlias = int | float | bool | str | None


class DevClaim(StrictModel):
    """A code-authored statement with its complete, code-bound references."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    role: Role
    headlineTemplate: str = Field(min_length=5, max_length=140)
    statementTemplate: str = Field(min_length=10, max_length=500)
    metricRefs: list[str] = Field(min_length=1)
    evidenceIds: list[str]
    metricBindings: dict[str, MetricValue] = Field(min_length=1)

    @field_validator("headlineTemplate", "statementTemplate")
    @classmethod
    def templates_have_no_free_numbers(cls, value: str) -> str:
        if any(char.isdigit() for char in value) or _NUMBER_WORDS.search(value):
            raise ValueError("code templates must not contain digits or number words")
        return value

    @model_validator(mode="after")
    def exact_claim_bindings(self) -> "DevClaim":
        if len(self.metricRefs) != len(set(self.metricRefs)):
            raise ValueError("claim metric references must be unique")
        if len(self.evidenceIds) != len(set(self.evidenceIds)):
            raise ValueError("claim evidence references must be unique")
        if set(self.metricBindings) != set(self.metricRefs):
            raise ValueError("every claim metric reference must have exactly one code-bound value")
        _ensure_finite_json(self.metricBindings)
        return self


class ClaimSelection(StrictModel):
    """The sole provider-controlled response shape: IDs and a non-decision status."""

    role: Role
    claim_ids: list[str] = Field(min_length=1)
    status: Literal["Aligned", "Watch"]

    @model_validator(mode="after")
    def no_duplicate_claims(self) -> "ClaimSelection":
        if len(self.claim_ids) != len(set(self.claim_ids)):
            raise ValueError("claim IDs must be unique")
        return self


class DevLineage(StrictModel):
    """Sanitized lineage emitted with the internal analysis; it contains no source paths."""

    kind: Literal[LINEAGE_KIND]
    analysisDataVersion: str = Field(min_length=1)
    candidateDataVersion: str = Field(min_length=1)
    candidateScopeSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidateSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    engineSourceDataVersion: str = Field(min_length=1)
    previewId: str = Field(min_length=1)
    previewSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    requestSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policySha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    contractSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidenceSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    traceAuditSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    engineSourceSha256: dict[str, str] = Field(min_length=1)
    intermediateManifestSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    traceAuditorSha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    versionRelationship: Literal["DISTINCT_VERSIONS_SAME_RAW_SOURCE_BYTES_AND_CONTRACT; ENGINE_VERSION_NOT_REWRITTEN"]
    humanReviewStatus: Literal["pending"]
    policyReviewStatus: Literal["UNAPPROVED_TEST_INPUT"]
    decisionReady: Literal[False]

    @field_validator("engineSourceSha256")
    @classmethod
    def engine_source_hashes_are_digests(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not key or not _SHA256.fullmatch(digest) for key, digest in value.items()):
            raise ValueError("engine source lineage hashes must be SHA-256 digests")
        return value


class DevRoleOutput(StrictModel):
    role: Role
    availability: Literal["DEV_ONLY", "UNAVAILABLE"]
    headline: str = Field(min_length=5, max_length=300)
    reasonText: str = Field(min_length=10, max_length=3000)
    claimIds: list[str]
    metricRefs: list[str]
    evidenceIds: list[str]
    metricBindings: dict[str, MetricValue]
    status: Literal["Aligned", "Watch"] | None
    failure: Literal["timeout", "provider_error", "cancelled", "invalid_response"] | None

    @field_validator("headline", "reasonText")
    @classmethod
    def output_text_is_code_safe(cls, value: str) -> str:
        if any(char.isdigit() for char in value) or _NUMBER_WORDS.search(value):
            raise ValueError("rendered development text must not contain digits or number words")
        return value

    @model_validator(mode="after")
    def status_and_availability_agree(self) -> "DevRoleOutput":
        unavailable = self.availability == "UNAVAILABLE"
        if unavailable != (self.failure is not None):
            raise ValueError("availability and failure must agree")
        if (self.status is None) == (self.failure is None):
            raise ValueError("successful output needs status; unavailable output cannot have status")
        if unavailable and (self.claimIds or self.metricRefs or self.evidenceIds or self.metricBindings):
            raise ValueError("unavailable output must not fabricate claims or bindings")
        if len(self.claimIds) != len(set(self.claimIds)):
            raise ValueError("selected claim IDs must be unique")
        if len(self.metricRefs) != len(set(self.metricRefs)):
            raise ValueError("output metric references must be unique")
        if len(self.evidenceIds) != len(set(self.evidenceIds)):
            raise ValueError("output evidence IDs must be unique")
        if set(self.metricBindings) != set(self.metricRefs):
            raise ValueError("output bindings must cover exactly its metric references")
        _ensure_finite_json(self.metricBindings)
        return self


class DevAnalysis(StrictModel):
    """Internal JSON only; deliberately not a public BoardroomResponse."""

    kind: Literal["CAUSORA_DAY3_UNREVIEWED_DEV_ANALYSIS_V1"]
    humanReviewStatus: Literal["pending"]
    decisionReady: Literal[False]
    sourceMode: Literal["UNREVIEWED_DEV_COMPUTED"]
    commentaryMode: Literal["CODE_BOUND_CLAIM_SELECTION"]
    analysisDataVersion: str = Field(min_length=1)
    lineage: DevLineage
    scenarioId: str = Field(min_length=1)
    providerKind: str = Field(min_length=1)
    state: Literal["ALL_READY", "PARTIAL", "UNAVAILABLE"]
    outputs: list[DevRoleOutput] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def result_is_unreviewed_and_ordered(self) -> "DevAnalysis":
        if self.analysisDataVersion != self.lineage.analysisDataVersion:
            raise ValueError("analysis data version must be lineage-bound")
        if [item.role for item in self.outputs] != list(ROLES):
            raise ValueError("role outputs must remain in CFO/COO/Risk order")
        successes = sum(item.failure is None for item in self.outputs)
        expected = "ALL_READY" if successes == 3 else "UNAVAILABLE" if successes == 0 else "PARTIAL"
        if self.state != expected:
            raise ValueError("analysis state must reflect all role outcomes")
        return self


class Provider(Protocol):
    kind: str

    async def complete(self, *, role: Role, system: str, payload: dict[str, Any],
                       schema: dict[str, Any]) -> dict[str, Any]: ...


class DevClaimStubProvider:
    """Deterministic selector for tests and offline development; it creates no prose.

    ``claim_ids`` can be a role-to-ID mapping or an ordered common sequence.  Values not
    present in a role's allowlist are ignored rather than becoming fictional claims.
    """

    kind = "OFFLINE_STUB"

    def __init__(self, claim_ids: Mapping[str, Sequence[str]] | Sequence[str] | None = None,
                 *, select_all: bool = True, status: Literal["Aligned", "Watch"] = "Watch") -> None:
        self._claim_ids = claim_ids
        self._select_all = select_all
        self._status = status

    async def complete(self, *, role: Role, system: str, payload: dict[str, Any],
                       schema: dict[str, Any]) -> dict[str, Any]:
        del system, schema
        catalog = payload["claimCatalog"]
        if not isinstance(catalog, list):
            raise ValueError("development stub requires a claim catalog")
        allowed = [item.get("id") for item in catalog if isinstance(item, dict)]
        if not allowed or len(allowed) != len(catalog) or not all(isinstance(item, str) for item in allowed):
            raise ValueError("development stub requires code-authored claim IDs")
        requested: Sequence[str]
        if self._claim_ids is None:
            requested = allowed if self._select_all else allowed[:1]
        elif isinstance(self._claim_ids, Mapping):
            requested = self._claim_ids.get(role, allowed if self._select_all else allowed[:1])
        else:
            requested = self._claim_ids
        chosen = [item for item in requested if item in allowed]
        if not chosen:
            chosen = allowed[:1]
        return {"role": role, "claim_ids": chosen, "status": self._status}


def response_schema(role: Role, claim_ids: Sequence[str]) -> dict[str, Any]:
    """Return the narrow model-provider schema; narrative and numbers are impossible fields."""
    ids = list(claim_ids)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("response schema requires a non-empty unique claim allowlist")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["role", "claim_ids", "status"],
        "properties": {
            "role": {"type": "string", "enum": [role]},
            "claim_ids": {"type": "array", "minItems": 1,
                          "items": {"type": "string", "enum": ids}},
            "status": {"type": "string", "enum": ["Aligned", "Watch"]},
        },
    }


def _ensure_finite_json(value: Any) -> None:
    """Reject non-finite values recursively before a result can be returned or hashed."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("all development JSON numbers must be finite")
    elif isinstance(value, Mapping):
        for child in value.values():
            _ensure_finite_json(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _ensure_finite_json(child)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array")
    return value


def _require_exact(value: Any, expected: Any, label: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise ValueError(f"{label} must equal the development-only pending value")


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a lower-case SHA-256 digest")
    return value


def _lineage_from_bundle(raw: dict[str, Any]) -> DevLineage:
    """Validate the complete bridge lineage and return its path-free typed projection."""
    allowed = {
        "kind", "analysisDataVersion", "candidateDataVersion", "candidateScopeSha256",
        "candidateSha256", "engineSourceDataVersion", "previewId", "previewSha256",
        "requestSha256", "policySha256", "contractSha256", "evidenceSha256",
        "traceAuditSha256", "sourceHashMapping", "engineSourceSha256",
        "intermediateManifestSha256", "traceAuditorSha256", "versionRelationship",
        "humanReviewStatus", "policyReviewStatus", "decisionReady",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError("development lineage contains unknown fields")
    missing = allowed - set(raw)
    if missing:
        raise ValueError("development lineage is missing required bridge metadata")
    _require_exact(raw.get("kind"), LINEAGE_KIND, "lineage.kind")
    _require_exact(raw.get("humanReviewStatus"), "pending", "lineage.humanReviewStatus")
    _require_exact(raw.get("policyReviewStatus"), "UNAPPROVED_TEST_INPUT", "lineage.policyReviewStatus")
    _require_exact(raw.get("decisionReady"), False, "lineage.decisionReady")
    _require_exact(
        raw.get("versionRelationship"),
        "DISTINCT_VERSIONS_SAME_RAW_SOURCE_BYTES_AND_CONTRACT; ENGINE_VERSION_NOT_REWRITTEN",
        "lineage.versionRelationship",
    )
    for name in (
        "candidateScopeSha256", "candidateSha256", "previewSha256", "requestSha256",
        "policySha256", "contractSha256", "evidenceSha256", "traceAuditSha256",
        "intermediateManifestSha256", "traceAuditorSha256",
    ):
        _require_sha(raw.get(name), f"lineage.{name}")
    candidate_version = raw.get("candidateDataVersion")
    engine_version = raw.get("engineSourceDataVersion")
    if not isinstance(candidate_version, str) or not candidate_version:
        raise ValueError("lineage candidate data version is required")
    if not isinstance(engine_version, str) or not engine_version:
        raise ValueError("lineage engine source data version is required")
    # The candidate's manifest scope is encoded in its immutable candidate version.  This
    # proves that the two deliberately distinct data versions are still provenance-bound.
    if not candidate_version.endswith(f"-wang-ai-review-{raw['candidateScopeSha256'][:12]}"):
        raise ValueError("candidate data version is not bound to its manifest scope digest")
    if candidate_version == engine_version:
        raise ValueError("candidate and engine source data versions must remain distinct")
    if not isinstance(raw.get("previewId"), str) or not raw["previewId"]:
        raise ValueError("lineage preview ID is required")

    source_mapping = _dict(raw.get("sourceHashMapping"), "lineage.sourceHashMapping")
    if not source_mapping:
        raise ValueError("lineage source hash mapping is required")
    for alias, item in source_mapping.items():
        record = _dict(item, "lineage source hash mapping record")
        if not isinstance(alias, str) or not alias or not isinstance(record.get("backendPath"), str):
            raise ValueError("lineage source hash mapping identity is invalid")
        _require_sha(record.get("sha256"), "lineage source hash mapping digest")
    engine_hashes = _dict(raw.get("engineSourceSha256"), "lineage.engineSourceSha256")
    if not engine_hashes:
        raise ValueError("lineage engine source hashes are required")
    for name, digest in engine_hashes.items():
        if not isinstance(name, str) or not name:
            raise ValueError("lineage engine source hash identity is invalid")
        _require_sha(digest, "lineage engine source digest")

    version_input = {key: value for key, value in raw.items() if key != "analysisDataVersion"}
    expected_version = f"dev-analysis-{sha256_json(version_input)[:20]}"
    _require_exact(raw.get("analysisDataVersion"), expected_version, "lineage.analysisDataVersion")
    # sourceHashMapping intentionally remains raw-only because its backendPath values are
    # provenance internals.  Strict model fields are the only lineage values emitted.
    return DevLineage.model_validate({name: raw[name] for name in DevLineage.model_fields})


def _validate_hashes(*, preview: dict[str, Any], request: dict[str, Any], contract: dict[str, Any],
                     evidence: list[Any], trace_audit: dict[str, Any], lineage: DevLineage,
                     raw_lineage: dict[str, Any]) -> None:
    if sha256_json(preview) != lineage.previewSha256:
        raise ValueError("development preview hash does not match lineage")
    if sha256_json(request) != lineage.requestSha256:
        raise ValueError("development request hash does not match lineage")
    if sha256_json(preview.get("policy")) != lineage.policySha256:
        raise ValueError("development policy hash does not match lineage")
    if sha256_json(contract) != lineage.contractSha256:
        raise ValueError("development contract hash does not match lineage")
    if sha256_json(evidence) != lineage.evidenceSha256:
        raise ValueError("development evidence hash does not match lineage")
    if sha256_json(trace_audit) != lineage.traceAuditSha256:
        raise ValueError("development trace-audit hash does not match lineage")
    if lineage.previewId != preview.get("previewId"):
        raise ValueError("development preview ID does not match lineage")
    if lineage.engineSourceSha256 != preview.get("engineSourceSha256"):
        raise ValueError("development engine source hashes do not match lineage")
    if lineage.intermediateManifestSha256 != preview.get("intermediateManifestSha256"):
        raise ValueError("development intermediate manifest hash does not match lineage")
    source_mapping = _dict(raw_lineage.get("sourceHashMapping"), "lineage.sourceHashMapping")
    mapped_hashes = {_dict(item, "lineage source hash mapping record")["sha256"]
                     for item in source_mapping.values()}
    preview_hashes = set(_dict(preview.get("inputHashesSha256"), "preview.inputHashesSha256").values())
    if not preview_hashes <= mapped_hashes:
        raise ValueError("development preview input hashes are not bound to the candidate source mapping")


def _validate_preview_and_audit(preview: dict[str, Any], trace_audit: dict[str, Any]) -> None:
    """Fail closed on all pending-only metadata and trace coverage checks before a call."""
    _require_exact(preview.get("kind"), PREVIEW_KIND, "preview.kind")
    _require_exact(preview.get("status"), "UNREVIEWED_TEST_ONLY_NO_RECOMMENDATION", "preview.status")
    _require_exact(preview.get("decisionReady"), False, "preview.decisionReady")
    _require_exact(preview.get("reviewStatus"), "PENDING_HUMAN_REVIEW", "preview.reviewStatus")
    _require_exact(preview.get("reviewSha256"), None, "preview.reviewSha256")
    _require_exact(preview.get("sourceDataVersion"), BASELINE_SOURCE_DATA_VERSION, "preview.sourceDataVersion")
    _require_exact(preview.get("deterministicRuns"), 1, "preview.deterministicRuns")
    _require_exact(preview.get("monteCarloRuns"), 0, "preview.monteCarloRuns")
    _require_exact(preview.get("assumptionStatus"), "UNAPPROVED_TEST_INPUT", "preview.assumptionStatus")
    if not isinstance(preview.get("policy"), dict):
        raise ValueError("preview policy is required for the unreviewed development boundary")
    for hash_map_name in ("engineSourceSha256", "inputHashesSha256"):
        hash_map = _dict(preview.get(hash_map_name), f"preview.{hash_map_name}")
        if not hash_map or any(not isinstance(key, str) or not _SHA256.fullmatch(value)
                               for key, value in hash_map.items()):
            raise ValueError(f"preview.{hash_map_name} must contain SHA-256 source digests")
    _require_sha(preview.get("intermediateManifestSha256"), "preview.intermediateManifestSha256")

    _require_exact(trace_audit.get("kind"), TRACE_AUDIT_KIND, "traceAudit.kind")
    _require_exact(trace_audit.get("devOnly"), True, "traceAudit.devOnly")
    _require_exact(trace_audit.get("decisionReady"), False, "traceAudit.decisionReady")
    _require_exact(trace_audit.get("matrixCells"), 9, "traceAudit.matrixCells")
    _require_exact(trace_audit.get("traceRows"), 936, "traceAudit.traceRows")
    audit_cells = _list(trace_audit.get("cells"), "traceAudit.cells")
    if len(audit_cells) != 9:
        raise ValueError("trace audit must retain every deterministic matrix cell")

    matrix = _dict(preview.get("matrix"), "preview.matrix")
    if set(matrix) != {"baseline", "demand-drop", "lead-stress"}:
        raise ValueError("preview must retain the full three-scenario deterministic matrix")
    preview_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for scenario_id in ("baseline", "demand-drop", "lead-stress"):
        cells = _list(matrix.get(scenario_id), f"preview.matrix.{scenario_id}")
        if len(cells) != 3:
            raise ValueError("each preview scenario must retain three deterministic cells")
        for cell in cells:
            raw_cell = _dict(cell, "preview matrix cell")
            option_id = raw_cell.get("optionId")
            if raw_cell.get("scenarioId") != scenario_id or option_id not in _OPTION_IDS:
                raise ValueError("preview matrix cell identity is invalid")
            if (scenario_id, option_id) in preview_by_key:
                raise ValueError("preview matrix cells must be unique")
            if "stockoutProbability" in raw_cell or "cashOutflowP90" in raw_cell or "cashOutflowP90Usd" in raw_cell:
                raise ValueError("deterministic preview must not be relabelled as probability or P90 output")
            if len(_list(raw_cell.get("weeklyTrace"), "preview weeklyTrace")) != 104:
                raise ValueError("every audited deterministic cell must retain 104 trace rows")
            preview_by_key[(scenario_id, option_id)] = raw_cell
    if set(preview_by_key) != {(scenario, option) for scenario in matrix for option in _OPTION_IDS}:
        raise ValueError("preview matrix must contain exactly nine fixed cells")

    audit_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for audit_cell in audit_cells:
        item = _dict(audit_cell, "trace audit cell")
        key = (item.get("scenarioId"), item.get("optionId"))
        if key in audit_by_key or key not in preview_by_key:
            raise ValueError("trace audit cells do not bind the preview matrix")
        audit_by_key[key] = item
    if set(audit_by_key) != set(preview_by_key):
        raise ValueError("trace audit must cover the exact nine preview cells")
    # This cross-check prevents a pass-looking audit summary from being paired with a
    # different same-shaped preview after hashes were calculated.
    for key, preview_cell in preview_by_key.items():
        audit_cell = audit_by_key[key]
        for field in ("demandUnits", "fulfilledUnits", "lostUnits", "orderedUnitsA", "orderedUnitsB",
                      "deliveredUnitsA", "deliveredUnitsB", "endingInventoryUnits", "unitsInTransitAtEnd",
                      "stockoutOccurred", "serviceLevel", "cashOutflowUsd", "tcoUsd", "grossProfitUsd", "feasible"):
            if audit_cell.get(field) != preview_cell.get(field):
                raise ValueError("trace audit summary does not reconcile to the preview")


def _validate_candidate_records(request: dict[str, Any], contract: dict[str, Any], evidence: list[Any]) -> None:
    options = _list(request.get("options"), "request.options")
    scenarios = _list(request.get("scenarios"), "request.scenarios")
    if {item.get("id") for item in options if isinstance(item, dict)} != set(_OPTION_IDS) or len(options) != 3:
        raise ValueError("existing request must retain D0/D1/D2 options")
    if {item.get("id") for item in scenarios if isinstance(item, dict)} != {
        "baseline", "demand-drop", "lead-stress"
    } or len(scenarios) != 3:
        raise ValueError("existing request must retain all deterministic scenarios")
    if len(evidence) != 5:
        raise ValueError("candidate evidence must contain the existing public five records")
    evidence_ids: list[str] = []
    for item in evidence:
        record = _dict(item, "candidate evidence")
        evidence_id = record.get("id")
        if not isinstance(evidence_id, str) or not re.fullmatch(r"EV-\d{3}", evidence_id):
            raise ValueError("candidate evidence ID is invalid")
        if type(record.get("quoteMatched")) is not bool:
            raise ValueError("candidate evidence must retain quoteMatched as a boolean")
        evidence_ids.append(evidence_id)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("candidate evidence IDs must be unique")
    contract_ids = _list(contract.get("evidenceIds"), "contract.evidenceIds")
    if contract_ids != evidence_ids:
        raise ValueError("candidate contract must bind the exact public evidence ordering")


def _selected_scenario(request: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("scenario_id must be a non-empty string")
    try:
        scenario = next(item for item in _list(request["scenarios"], "request.scenarios")
                        if isinstance(item, dict) and item.get("id") == scenario_id)
    except StopIteration as exc:
        raise ValueError("scenario_id is not present in the existing request") from exc
    return scenario


def _selected_cells(preview: dict[str, Any], scenario_id: str) -> list[dict[str, Any]]:
    matrix = _dict(preview["matrix"], "preview.matrix")
    cells = _list(matrix.get(scenario_id), f"preview.matrix.{scenario_id}")
    by_option = {cell.get("optionId"): cell for cell in cells if isinstance(cell, dict)}
    if set(by_option) != set(_OPTION_IDS):
        raise ValueError("selected scenario does not contain the fixed deterministic option cells")
    return [by_option[option] for option in _OPTION_IDS]


def _build_projections(*, preview: dict[str, Any], request: dict[str, Any], contract: dict[str, Any],
                       evidence: list[Any], scenario_id: str) -> dict[Role, DevProjection]:
    """Build strict, minimal role projections from one actual audited preview scenario."""
    scenario = _selected_scenario(request, scenario_id)
    cells = _selected_cells(preview, scenario_id)
    d0_tco = cells[0].get("tcoUsd")
    if type(d0_tco) is not int:
        raise ValueError("D0 deterministic TCO must be an integer")

    cfo = DevCfoProjection.model_validate({
        "scenarioId": scenario_id,
        "options": [{
            "optionId": cell.get("optionId"),
            "tcoUsd": cell.get("tcoUsd"),
            "cashOutflowUsd": cell.get("cashOutflowUsd"),
            "deltaTcoUsdFromD0": cell.get("tcoUsd") - d0_tco if type(cell.get("tcoUsd")) is int else None,
            "costBreakdownUsd": cell.get("costBreakdownUsd"),
            "revenueUsd": cell.get("revenueUsd"),
            "grossProfitUsd": cell.get("grossProfitUsd"),
            "grossMargin": cell.get("grossMargin"),
            "grossMarginStatus": cell.get("grossMarginStatus"),
        } for cell in cells],
    })
    coo = DevCooProjection.model_validate({
        "scenarioId": scenario_id,
        "demandUnits24m": scenario.get("demandUnits24m"),
        "demandShock": scenario.get("demandShock"),
        "leadTime": scenario.get("leadTime"),
        "leadTimeMultiplier": scenario.get("leadTimeMultiplier"),
        "options": [{
            "optionId": cell.get("optionId"),
            "orderedUnitsA": cell.get("orderedUnitsA"),
            "orderedUnitsB": cell.get("orderedUnitsB"),
            "deliveredUnitsA": cell.get("deliveredUnitsA"),
            "deliveredUnitsB": cell.get("deliveredUnitsB"),
            "endingInventoryUnits": cell.get("endingInventoryUnits"),
            "unitsInTransitAtEnd": cell.get("unitsInTransitAtEnd"),
            "fulfilledUnits": cell.get("fulfilledUnits"),
            "lostUnits": cell.get("lostUnits"),
            "serviceLevel": cell.get("serviceLevel"),
            "stockoutOccurred": cell.get("stockoutOccurred"),
        } for cell in cells],
    })
    policy = _dict(preview.get("policy"), "preview.policy")
    matched_ids = [
        _dict(item, "candidate evidence").get("id") for item in evidence
        if _dict(item, "candidate evidence").get("quoteMatched") is True
    ]
    risk = DevRiskProjection.model_validate({
        "scenarioId": scenario_id,
        "humanReviewStatus": "pending",
        "decisionReady": False,
        "matchedEvidenceIds": matched_ids,
        "scenario": {
            "demandShock": scenario.get("demandShock"),
            "leadTime": scenario.get("leadTime"),
            "leadTimeMultiplier": scenario.get("leadTimeMultiplier"),
        },
        "policy": {
            "assumptionStatus": policy.get("assumptionStatus"),
            "cashTiming": policy.get("cashTiming"),
            "purchaseRecognition": policy.get("purchaseRecognition"),
            "roundingMode": policy.get("roundingMode"),
            "demandMode": policy.get("demandMode"),
            "leadTimeMode": policy.get("leadTimeMode"),
            "leadStressAppliesTo": policy.get("leadStressAppliesTo"),
            "commitmentSchedule": policy.get("commitmentSchedule"),
            "holdingBasis": policy.get("holdingBasis"),
            "deterministicRuns": preview.get("deterministicRuns"),
            "monteCarloRuns": preview.get("monteCarloRuns"),
        },
        "contract": {
            "renewalLocked": contract.get("renewalLocked"),
            "renewalNoticeDays": contract.get("renewalNoticeDays"),
            "renewalTermMonths": contract.get("renewalTermMonths"),
            "renewalPriceIncreasePct": contract.get("renewalPriceIncreasePct"),
            "minPurchaseShareA": contract.get("minPurchaseShareA"),
            "forecastBasis": contract.get("forecastBasis"),
            "lockedForecastUnits24m": contract.get("lockedForecastUnits24m"),
            "minPurchaseUnitsA": contract.get("minPurchaseUnitsA"),
            "terminationFeeUsd": contract.get("terminationFeeUsd"),
        },
        "options": [{
            "optionId": cell.get("optionId"),
            "feasible": cell.get("feasible"),
            "cashOutflowUsd": cell.get("cashOutflowUsd"),
            "stockoutOccurred": cell.get("stockoutOccurred"),
        } for cell in cells],
    })
    return {"CFO": cfo, "COO": coo, "Risk": risk}


def validate_development_bundle(bundle: dict[str, Any], *, scenario_id: str = "demand-drop") -> tuple[
        dict[Role, DevProjection], DevLineage]:
    """Validate the pending-only bridge bundle and return detached narrow projections.

    This function is deliberately synchronous and fail-closed.  It is called before
    any role task is created, so an invalid bundle is rejected rather than converted
    into plausible unavailable commentary.
    """
    if not isinstance(bundle, dict):
        raise ValueError("development bundle must be a JSON object")
    _ensure_finite_json(bundle)
    _require_exact(bundle.get("kind"), BUNDLE_KIND, "bundle.kind")
    _require_exact(bundle.get("humanReviewStatus"), "pending", "bundle.humanReviewStatus")
    _require_exact(bundle.get("decisionReady"), False, "bundle.decisionReady")
    _require_exact(bundle.get("permittedUse"), "DEVELOPMENT_TEST_ONLY", "bundle.permittedUse")
    _require_exact(bundle.get("sourceMode"), "UNREVIEWED_DEV_COMPUTED", "bundle.sourceMode")
    # A receipt or approval-looking value cannot be carried into this unreviewed path.
    forbidden = {"humanReceipt", "humanReviewReceipt", "reviewReceipt", "approval", "approved"}
    if forbidden & set(bundle):
        raise ValueError("unreviewed development bundle cannot contain a human receipt or approval")

    preview = _dict(bundle.get("preview"), "bundle.preview")
    request = _dict(bundle.get("request"), "bundle.request")
    contract = _dict(bundle.get("contract"), "bundle.contract")
    evidence = _list(bundle.get("evidence"), "bundle.evidence")
    trace_audit = _dict(bundle.get("traceAudit"), "bundle.traceAudit")
    raw_lineage = _dict(bundle.get("lineage"), "bundle.lineage")
    lineage = _lineage_from_bundle(raw_lineage)

    _validate_preview_and_audit(preview, trace_audit)
    _validate_candidate_records(request, contract, evidence)
    _validate_hashes(preview=preview, request=request, contract=contract, evidence=evidence,
                     trace_audit=trace_audit, lineage=lineage, raw_lineage=raw_lineage)
    if lineage.engineSourceDataVersion != preview["sourceDataVersion"]:
        raise ValueError("engine source data version must bind the deterministic preview source version")
    if lineage.engineSourceDataVersion != BASELINE_SOURCE_DATA_VERSION:
        raise ValueError("engine source data version must remain the baseline deterministic source version")
    return _build_projections(preview=preview, request=request, contract=contract, evidence=evidence,
                              scenario_id=scenario_id), lineage


def build_dev_projections(bundle: dict[str, Any], *, scenario_id: str = "demand-drop") -> dict[Role, DevProjection]:
    """Public introspection helper returning only strict role-local projections."""
    projections, _lineage = validate_development_bundle(bundle, scenario_id=scenario_id)
    return projections


def _cfo_bindings(view: DevCfoProjection) -> dict[str, MetricValue]:
    values: dict[str, MetricValue] = {}
    for item in view.options:
        values[f"tcoUsd:{item.optionId}"] = item.tcoUsd
        values[f"cashOutflowUsd:{item.optionId}"] = item.cashOutflowUsd
        values[f"deltaTcoUsdFromD0:{item.optionId}"] = item.deltaTcoUsdFromD0
        for field in _COST_FIELDS:
            values[f"costBreakdownUsd.{field}:{item.optionId}"] = getattr(item.costBreakdownUsd, field)
        values[f"revenueUsd:{item.optionId}"] = item.revenueUsd
        values[f"grossProfitUsd:{item.optionId}"] = item.grossProfitUsd
        values[f"grossMargin:{item.optionId}"] = item.grossMargin
    return values


def _coo_bindings(view: DevCooProjection) -> dict[str, MetricValue]:
    values: dict[str, MetricValue] = {
        "demandUnits24m": view.demandUnits24m,
        "demandShock": view.demandShock,
        "leadTime": view.leadTime,
        "leadTimeMultiplier": view.leadTimeMultiplier,
    }
    for item in view.options:
        for field in ("orderedUnitsA", "orderedUnitsB", "deliveredUnitsA", "deliveredUnitsB",
                      "endingInventoryUnits", "unitsInTransitAtEnd", "fulfilledUnits", "lostUnits",
                      "serviceLevel", "stockoutOccurred"):
            values[f"{field}:{item.optionId}"] = getattr(item, field)
    return values


def _risk_bindings(view: DevRiskProjection) -> dict[str, MetricValue]:
    values: dict[str, MetricValue] = {
        "humanReviewStatus": view.humanReviewStatus,
        "decisionReady": view.decisionReady,
        "scenario.demandShock": view.scenario.demandShock,
        "scenario.leadTime": view.scenario.leadTime,
        "scenario.leadTimeMultiplier": view.scenario.leadTimeMultiplier,
        "policy.assumptionStatus": view.policy.assumptionStatus,
        "policy.cashTiming": view.policy.cashTiming,
        "policy.purchaseRecognition": view.policy.purchaseRecognition,
        "policy.roundingMode": view.policy.roundingMode,
        "policy.demandMode": view.policy.demandMode,
        "policy.leadTimeMode": view.policy.leadTimeMode,
        "policy.leadStressAppliesTo": view.policy.leadStressAppliesTo,
        "policy.commitmentSchedule": view.policy.commitmentSchedule,
        "policy.holdingBasis": view.policy.holdingBasis,
        "policy.deterministicRuns": view.policy.deterministicRuns,
        "policy.monteCarloRuns": view.policy.monteCarloRuns,
    }
    for field in ("renewalLocked", "renewalNoticeDays", "renewalTermMonths", "renewalPriceIncreasePct",
                  "minPurchaseShareA", "forecastBasis", "lockedForecastUnits24m", "minPurchaseUnitsA",
                  "terminationFeeUsd"):
        values[f"contract.{field}"] = getattr(view.contract, field)
    for item in view.options:
        values[f"feasible:{item.optionId}"] = item.feasible
        values[f"cashOutflowUsd:{item.optionId}"] = item.cashOutflowUsd
        values[f"stockoutOccurred:{item.optionId}"] = item.stockoutOccurred
    return values


def _claim(*, claim_id: str, role: Role, headline: str, statement: str, refs: Sequence[str],
           evidence_ids: Sequence[str], bindings: Mapping[str, MetricValue]) -> DevClaim:
    ref_list = list(refs)
    return DevClaim(
        id=claim_id, role=role, headlineTemplate=headline, statementTemplate=statement,
        metricRefs=ref_list, evidenceIds=list(evidence_ids),
        metricBindings={ref: bindings[ref] for ref in ref_list},
    )


def build_claim_catalog(view: DevProjection) -> list[DevClaim]:
    """Create the complete code-authored claim catalog for one role projection.

    Predicates such as purchase-versus-demand and lost sales are evaluated here, not
    by a provider.  A false predicate has no selectable claim ID.
    """
    if isinstance(view, DevCfoProjection):
        b = _cfo_bindings(view)
        option_ids = [item.optionId for item in view.options]
        all_tco_cash_loss = [ref for option in option_ids for ref in (
            f"tcoUsd:{option}", f"cashOutflowUsd:{option}", f"costBreakdownUsd.stockoutLoss:{option}")]
        all_deltas = [f"deltaTcoUsdFromD0:{option}" for option in option_ids]
        all_breakdown = [f"costBreakdownUsd.{field}:{option}" for option in option_ids for field in _COST_FIELDS]
        all_operating = [ref for option in option_ids for ref in (
            f"revenueUsd:{option}", f"grossProfitUsd:{option}", f"grossMargin:{option}")]
        claims = [
            _claim(claim_id="cfo_cost_cash_opportunity_separated", role="CFO",
                   headline="Financial development claims",
                   statement="Total cost, cash outflow, and opportunity loss remain separately bound to the listed financial metrics.",
                   refs=all_tco_cash_loss, evidence_ids=(), bindings=b),
            _claim(claim_id="cfo_baseline_delta_bound", role="CFO",
                   headline="Financial development claims",
                   statement="The baseline delta remains bound to the listed total-cost metrics.",
                   refs=all_deltas, evidence_ids=(), bindings=b),
            _claim(claim_id="cfo_cost_components_bound", role="CFO",
                   headline="Financial development claims",
                   statement="Cost components remain separately bound to the listed financial metrics.",
                   refs=all_breakdown, evidence_ids=(), bindings=b),
            _claim(claim_id="cfo_operating_result_bound", role="CFO",
                   headline="Financial development claims",
                   statement="Revenue, gross profit, and margin remain bound to the listed financial metrics.",
                   refs=all_operating, evidence_ids=(), bindings=b),
        ]
        lower_with_charges = [item.optionId for item in view.options
            if item.deltaTcoUsdFromD0 < 0 and item.costBreakdownUsd.terminationFee > 0
            and item.costBreakdownUsd.stockoutLoss > 0]
        if lower_with_charges:
            refs = ["tcoUsd:D0"] + [ref for option in lower_with_charges for ref in
                (f"tcoUsd:{option}", f"deltaTcoUsdFromD0:{option}",
                 f"costBreakdownUsd.terminationFee:{option}", f"costBreakdownUsd.stockoutLoss:{option}")]
            claims.append(_claim(claim_id="cfo_lower_cost_retains_exit_and_loss", role="CFO",
                headline="Financial development claims",
                statement="A lower-cost financial alternative retains exit and opportunity-loss charges; cost savings alone do not settle the decision.",
                refs=refs, evidence_ids=(), bindings=b))
        baseline_margin = view.options[0].grossMargin
        higher_with_lower_margin = [item.optionId for item in view.options
            if item.deltaTcoUsdFromD0 > 0 and item.grossMargin is not None
            and baseline_margin is not None and item.grossMargin < baseline_margin]
        if higher_with_lower_margin:
            refs = ["tcoUsd:D0", "grossMargin:D0"] + [ref for option in higher_with_lower_margin for ref in
                (f"tcoUsd:{option}", f"deltaTcoUsdFromD0:{option}", f"grossMargin:{option}")]
            claims.append(_claim(claim_id="cfo_higher_cost_lower_margin", role="CFO",
                headline="Financial development claims",
                statement="An option has higher total cost and lower gross margin than the baseline under the bound test policy.",
                refs=refs, evidence_ids=(), bindings=b))
        return claims
    if isinstance(view, DevCooProjection):
        b = _coo_bindings(view)
        option_ids = [item.optionId for item in view.options]
        demand_lead = ["demandUnits24m", "demandShock", "leadTime", "leadTimeMultiplier"]
        all_flow = [ref for option in option_ids for ref in (
            f"orderedUnitsA:{option}", f"orderedUnitsB:{option}", f"deliveredUnitsA:{option}",
            f"deliveredUnitsB:{option}", f"endingInventoryUnits:{option}", f"unitsInTransitAtEnd:{option}",
            f"fulfilledUnits:{option}", f"lostUnits:{option}")]
        all_service = [ref for option in option_ids for ref in (f"serviceLevel:{option}", f"stockoutOccurred:{option}")]
        claims = [
            _claim(claim_id="coo_demand_lead_bound", role="COO", headline="Operational development claims",
                   statement="Demand and lead conditions remain bound to the listed operational metrics.",
                   refs=demand_lead, evidence_ids=(), bindings=b),
            _claim(claim_id="coo_inventory_flow_bound", role="COO", headline="Operational development claims",
                   statement="Order, delivery, inventory, fulfillment, and loss values remain bound to the listed operational metrics.",
                   refs=all_flow, evidence_ids=(), bindings=b),
            _claim(claim_id="coo_service_stockout_bound", role="COO", headline="Operational development claims",
                   statement="Service and stockout observations remain bound to the listed operational metrics.",
                   refs=all_service, evidence_ids=(), bindings=b),
        ]
        excess = [item.optionId for item in view.options
                  if item.orderedUnitsA + item.orderedUnitsB > view.demandUnits24m]
        equal_for_all = all(item.orderedUnitsA + item.orderedUnitsB == view.demandUnits24m for item in view.options)
        if excess:
            refs = ["demandUnits24m"] + [ref for option in excess for ref in
                                           (f"orderedUnitsA:{option}", f"orderedUnitsB:{option}")]
            claims.append(_claim(claim_id="coo_purchases_exceed_demand", role="COO",
                                 headline="Operational development claims",
                                 statement="Procurement exceeds demand for the bound options.",
                                 refs=refs, evidence_ids=(), bindings=b))
        elif equal_for_all:
            refs = ["demandUnits24m"] + [ref for option in option_ids for ref in
                                           (f"orderedUnitsA:{option}", f"orderedUnitsB:{option}")]
            claims.append(_claim(claim_id="coo_purchases_equal_demand", role="COO",
                                 headline="Operational development claims",
                                 statement="Procurement equals demand across the bound options.",
                                 refs=refs, evidence_ids=(), bindings=b))
        lost = [item.optionId for item in view.options if item.lostUnits > 0]
        if lost:
            refs = [f"lostUnits:{option}" for option in lost]
            claims.append(_claim(claim_id="coo_lost_sales_present", role="COO",
                                 headline="Operational development claims",
                                 statement="Lost sales are present in the bound operational metrics.",
                                 refs=refs, evidence_ids=(), bindings=b))
        return claims
    if isinstance(view, DevRiskProjection):
        b = _risk_bindings(view)
        option_ids = [item.optionId for item in view.options]
        claims = [
            _claim(claim_id="risk_pending_human_review", role="Risk", headline="Risk development claims",
                   statement="Human review remains pending and the policy remains unapproved.",
                   refs=["humanReviewStatus", "decisionReady", "policy.assumptionStatus"],
                   evidence_ids=(), bindings=b),
            _claim(claim_id="risk_deterministic_no_probabilistic_tail", role="Risk", headline="Risk development claims",
                   statement="The deterministic preview has no probabilistic tail metric.",
                   refs=["policy.deterministicRuns", "policy.monteCarloRuns"], evidence_ids=(), bindings=b),
            _claim(claim_id="risk_fixed_procurement_commitment", role="Risk", headline="Risk development claims",
                   statement="The fixed procurement commitment remains bound to the contract clause metrics.",
                   refs=["contract.renewalLocked", "contract.minPurchaseShareA", "contract.forecastBasis",
                         "contract.lockedForecastUnits24m", "contract.minPurchaseUnitsA"],
                   evidence_ids=view.matchedEvidenceIds, bindings=b),
            _claim(claim_id="risk_option_cash_feasibility_stockout", role="Risk", headline="Risk development claims",
                   statement="Feasibility, cash exposure, and stockout observation remain bound to the listed risk metrics.",
                   refs=[ref for option in option_ids for ref in
                         (f"feasible:{option}", f"cashOutflowUsd:{option}", f"stockoutOccurred:{option}")],
                   evidence_ids=(), bindings=b),
            _claim(claim_id="risk_matched_evidence_clause_linkage", role="Risk", headline="Risk development claims",
                   statement="Matched evidence identifiers support clause linkage only and do not evidence human approval.",
                   refs=["humanReviewStatus", "contract.renewalNoticeDays", "contract.renewalTermMonths",
                         "contract.renewalPriceIncreasePct"], evidence_ids=view.matchedEvidenceIds, bindings=b),
        ]
        if view.scenario.demandShock < 0 and view.contract.renewalLocked:
            claims.append(_claim(claim_id="risk_locked_floor_under_declining_demand", role="Risk",
                                 headline="Risk development claims",
                                 statement="The locked purchase floor remains exposed under the declining-demand condition.",
                                 refs=["scenario.demandShock", "scenario.leadTime", "scenario.leadTimeMultiplier",
                                       "contract.renewalLocked", "contract.forecastBasis",
                                       "contract.lockedForecastUnits24m", "contract.minPurchaseUnitsA"],
                                 evidence_ids=view.matchedEvidenceIds, bindings=b))
        if view.contract.terminationFeeUsd > 0 and view.contract.renewalLocked:
            claims.append(_claim(claim_id="risk_conditional_renewed_exit_fee", role="Risk",
                                 headline="Risk development claims",
                                 statement="The exit cash exposure remains conditional on the renewed contract state.",
                                 refs=["contract.renewalLocked", "contract.terminationFeeUsd"],
                                 evidence_ids=view.matchedEvidenceIds, bindings=b))
        return claims
    raise ValueError("unsupported strict development projection")


def _provider_payload(role: Role, view: DevProjection, claims: Sequence[DevClaim]) -> dict[str, Any]:
    """Return a role-local typed view and code-authored claim definitions only."""
    return {
        "role": role,
        "view": view.model_dump(mode="json"),
        "claimCatalog": [{
            "id": claim.id,
            "statementTemplate": claim.statementTemplate,
            "metricRefs": list(claim.metricRefs),
            "evidenceIds": list(claim.evidenceIds),
        } for claim in claims],
        "commentaryMode": "CODE_BOUND_CLAIM_SELECTION",
        "humanReviewStatus": "pending",
        "decisionReady": False,
    }


_SYSTEM = (
    "Select only allowed claim identifiers. Return exactly the requested JSON object. "
    "Do not return prose, reasons, headlines, metric values, options, recommendations, decisions, "
    "approval claims, evidence content, or additional fields."
)


def _render_selection(role: Role, selection: ClaimSelection, claims: Sequence[DevClaim]) -> DevRoleOutput:
    by_id = {claim.id: claim for claim in claims}
    if selection.role != role or not set(selection.claim_ids) <= set(by_id):
        raise ValueError("provider selected a claim outside the role-local allowlist")
    selected = [by_id[claim_id] for claim_id in selection.claim_ids]
    metric_refs: list[str] = []
    evidence_ids: list[str] = []
    bindings: dict[str, MetricValue] = {}
    for claim in selected:
        for ref in claim.metricRefs:
            if ref not in bindings:
                metric_refs.append(ref)
                bindings[ref] = claim.metricBindings[ref]
        for evidence_id in claim.evidenceIds:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    headline = selected[0].headlineTemplate
    reason = " ".join(claim.statementTemplate for claim in selected)
    return DevRoleOutput(
        role=role, availability="DEV_ONLY", headline=headline, reasonText=reason,
        claimIds=[claim.id for claim in selected], metricRefs=metric_refs, evidenceIds=evidence_ids,
        metricBindings=bindings, status=selection.status, failure=None,
    )


def _failure(role: Role, failure: Literal["timeout", "provider_error", "cancelled", "invalid_response"]) -> DevRoleOutput:
    return DevRoleOutput(
        role=role, availability="UNAVAILABLE", headline="Development analysis unavailable",
        reasonText="No development claim selection was returned.", claimIds=[], metricRefs=[], evidenceIds=[],
        metricBindings={}, status=None, failure=failure,
    )


async def run_dev_parallel(bundle: dict[str, Any], *, provider: Provider, enabled: bool = False,
                           scenario_id: str = "demand-drop", timeout_seconds: float = 15) -> dict[str, Any]:
    """Run isolated development claim selection for CFO, COO, and Risk.

    Explicit opt-in is mandatory.  All bundle gates run before provider invocation; gate
    failure raises rather than returning a skipped or unavailable analysis.  Per-role
    provider faults remain isolated, while cancellation of this outer coroutine is
    propagated to its caller.
    """
    if enabled is not True:
        raise PermissionError("unreviewed development role analysis requires enabled=True")
    if type(timeout_seconds) not in (int, float) or isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 45:
        raise ValueError("per-role timeout_seconds must be finite and in the range (0, 45]")
    if not math.isfinite(float(timeout_seconds)):
        raise ValueError("per-role timeout_seconds must be finite and in the range (0, 45]")
    provider_kind = getattr(provider, "kind", None)
    if not isinstance(provider_kind, str) or not provider_kind:
        raise ValueError("provider must declare a non-empty actual kind")

    projections, lineage = validate_development_bundle(bundle, scenario_id=scenario_id)
    catalogs: dict[Role, tuple[DevClaim, ...]] = {
        role: tuple(build_claim_catalog(projections[role])) for role in ROLES
    }
    if any(not catalog for catalog in catalogs.values()):
        raise ValueError("each role must have a non-empty code-authored claim catalog")

    async def one(role: Role) -> DevRoleOutput:
        claims = catalogs[role]
        allowed_ids = tuple(claim.id for claim in claims)
        payload = _provider_payload(role, projections[role], claims)
        schema = response_schema(role, allowed_ids)
        try:
            raw = await asyncio.wait_for(
                provider.complete(role=role, system=_SYSTEM, payload=payload, schema=schema),
                timeout=float(timeout_seconds),
            )
        except asyncio.TimeoutError:
            return _failure(role, "timeout")
        except asyncio.CancelledError:
            # A provider can cancel one role; cancellation of the outer run must never
            # be swallowed into a false completed analysis.
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise
            return _failure(role, "cancelled")
        except Exception:
            return _failure(role, "provider_error")
        try:
            selection = ClaimSelection.model_validate(raw)
            if selection.role != role or not set(selection.claim_ids) <= set(allowed_ids):
                raise ValueError("response crosses a role claim boundary")
            return _render_selection(role, selection, claims)
        except Exception:
            return _failure(role, "invalid_response")

    # Create every task before awaiting any.  gather preserves this stable input order.
    tasks = [asyncio.create_task(one(role)) for role in ROLES]
    outputs = await asyncio.gather(*tasks)
    successes = sum(output.failure is None for output in outputs)
    state: Literal["ALL_READY", "PARTIAL", "UNAVAILABLE"] = (
        "ALL_READY" if successes == 3 else "UNAVAILABLE" if successes == 0 else "PARTIAL"
    )
    result = DevAnalysis(
        kind="CAUSORA_DAY3_UNREVIEWED_DEV_ANALYSIS_V1", humanReviewStatus="pending", decisionReady=False,
        sourceMode="UNREVIEWED_DEV_COMPUTED", commentaryMode="CODE_BOUND_CLAIM_SELECTION",
        analysisDataVersion=lineage.analysisDataVersion, lineage=lineage, scenarioId=scenario_id,
        providerKind=provider_kind, state=state, outputs=outputs,
    )
    value = result.model_dump(mode="json")
    _ensure_finite_json(value)
    return value


__all__ = [
    "BASELINE_SOURCE_DATA_VERSION", "BUNDLE_KIND", "ClaimSelection", "DevAnalysis", "DevCfoProjection",
    "DevClaim", "DevClaimStubProvider", "DevCooProjection", "DevLineage", "DevRiskProjection",
    "DevRoleOutput", "LINEAGE_KIND", "PREVIEW_KIND", "ROLES", "TRACE_AUDIT_KIND",
    "build_claim_catalog", "build_dev_projections", "response_schema", "run_dev_parallel",
    "validate_development_bundle",
]
