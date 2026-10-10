"""Verification gates and minimal role projections for the independent Day 3 module."""
from __future__ import annotations

from pathlib import Path

from .models import (BoardroomSnapshot, CfoOption, CfoView, CooOption, CooView,
                     RiskContract, RiskOption, RiskView, cells_for)
from .wire_models import (DatasetSuccessEnvelope, HumanReceipt, ReviewScope,
                          load_local_mock_snapshot, read_json_object, sha256_json)

_REQUIRED_ASSUMPTIONS = {
    "decisionDate", "renewalDate", "noticeSent", "forecastBasis", "lockedForecastUnits24m",
}


def _strict_file_model(path: Path, model_type):
    raw = read_json_object(path)
    typed = model_type.model_validate(raw)
    if typed.model_dump(mode="json") != raw:
        raise ValueError(f"{path.name} changes during strict parsing")
    return typed, raw


def verify_human_review_bundle(review_bundle: Path, legacy_project_root: Path | None = None) -> DatasetSuccessEnvelope:
    """Validate the explicitly documented local human-review gate.

    This does *not* authenticate a human identity or a simulator. It proves only
    that a strict receipt binds a backend-provided dataset snapshot and source
    hashes. Jinzhu's verifier callback remains mandatory for simulation output.
    """
    bundle = review_bundle.resolve()
    if not bundle.is_dir():
        raise ValueError("review_bundle must be an existing directory")
    if (bundle / "bundle_manifest.json").is_file():
        if legacy_project_root is None:
            raise ValueError("Legacy review format requires explicit legacy_project_root")
        from .review_compat import verify_legacy_review_bundle
        return verify_legacy_review_bundle(legacy_project_root, bundle)
    required = {
        "dataset_success.json": DatasetSuccessEnvelope,
        "review_scope.json": ReviewScope,
        "human_receipt.json": HumanReceipt,
    }
    parsed = {}
    raw = {}
    for name, model_type in required.items():
        file = bundle / name
        if not file.is_file():
            raise ValueError(f"review_bundle missing required {name}")
        parsed[name], raw[name] = _strict_file_model(file, model_type)
    dataset: DatasetSuccessEnvelope = parsed["dataset_success.json"]
    scope: ReviewScope = parsed["review_scope.json"]
    receipt: HumanReceipt = parsed["human_receipt.json"]

    dataset_hash = sha256_json(raw["dataset_success.json"])
    scope_hash = sha256_json(raw["review_scope.json"])
    if scope.dataVersion != dataset.dataVersion or scope.datasetSha256 != dataset_hash:
        raise ValueError("Review scope must bind this exact backend dataset snapshot")
    if (receipt.scopeSha256 != scope_hash or receipt.datasetSha256 != dataset_hash or
            receipt.sourceHashes != scope.sourceHashes):
        raise ValueError("Human receipt must bind the current scope, dataset hash, and source hashes")
    # This is deliberately an exact six-item receipt protocol: five public v1
    # contract fields plus the evidence-review module's ledger-only sixth item.
    if set(receipt.approvedEvidenceIds) != {"EV-014", "EV-019", "EV-021", "EV-024", "EV-027", "EV-020"}:
        raise ValueError("Human receipt must record all six approved evidence IDs")
    if not set(item.id for item in dataset.data.evidence) <= set(receipt.approvedEvidenceIds):
        raise ValueError("Human receipt does not approve every dataset evidence ID")
    if set(receipt.approvedAssumptionKeys) != _REQUIRED_ASSUMPTIONS:
        raise ValueError("Human receipt does not approve all five scoped assumptions")
    if any(not evidence.quoteMatched for evidence in dataset.data.evidence):
        raise ValueError("A human-reviewed dataset cannot expose unmatched evidence to Risk")
    return dataset


def verify_snapshot(snapshot: BoardroomSnapshot, root: Path | None = None,
                    review_bundle: Path | None = None,
                    legacy_review_root: Path | None = None) -> None:
    """Fail closed before a provider sees any projection.

    ``root`` is retained only for call-site compatibility and is intentionally
    unused: local mock validation resolves this module's own frozen fixture.
    """
    del root
    if snapshot.sourceMode == "LOCAL_MOCK":
        if review_bundle is not None:
            raise ValueError("LOCAL_MOCK cannot be paired with a human-review bundle")
        frozen = load_local_mock_snapshot(snapshot.scenario.id)
        if snapshot != frozen:
            raise ValueError("LOCAL_MOCK snapshot must equal the unchanged frozen fixture")
        return

    if review_bundle is None:
        raise ValueError("SIMULATION_READY requires a human review_bundle")
    if snapshot.simulation.simulationId == load_local_mock_snapshot().simulation.simulationId:
        raise ValueError("Frozen LOCAL_MOCK simulation ID cannot be relabelled SIMULATION_READY")
    dataset = verify_human_review_bundle(review_bundle, legacy_project_root=legacy_review_root)
    reference = snapshot.simulationReference
    if reference is None:
        raise ValueError("SIMULATION_READY lacks a simulation-owner reference")
    if reference.datasetId != dataset.data.datasetId:
        raise ValueError("Simulation reference datasetId does not match reviewed dataset")
    if (snapshot.simulation.dataVersion != dataset.dataVersion or snapshot.contract != dataset.data.contract or
            snapshot.evidence != dataset.data.evidence):
        raise ValueError("Simulation must use the exact human-reviewed dataset version, contract, and evidence")


def project(snapshot: BoardroomSnapshot) -> dict[str, CfoView | CooView | RiskView]:
    """Return the only objects that may be serialized into provider messages."""
    cells = cells_for(snapshot)
    d0_tco = next(cell.expectedTco for cell in cells if cell.optionId == "D0")
    cfo = CfoView(
        scenarioId=snapshot.scenario.id,
        sourceMode=snapshot.sourceMode,
        options=[CfoOption(optionId=cell.optionId, expectedTcoUsd=cell.expectedTco,
                           cashOutflowP90Usd=cell.cashOutflowP90,
                           deltaTcoUsd=cell.expectedTco - d0_tco,
                           purchaseUsd=cell.breakdown.purchase, holdingUsd=cell.breakdown.holding,
                           stockoutLossUsd=cell.breakdown.stockoutLoss,
                           renewalPremiumUsd=cell.breakdown.renewalPremium,
                           terminationFeeUsd=cell.breakdown.terminationFee)
                 for cell in cells],
    )
    coo = CooView(
        scenarioId=snapshot.scenario.id,
        sourceMode=snapshot.sourceMode,
        demandUnits24m=snapshot.scenario.demandUnits24m,
        leadTimeMultiplier=snapshot.scenario.leadTimeMultiplier,
        options=[CooOption(optionId=cell.optionId, stockoutProbability=cell.stockoutProbability,
                           serviceLevel=cell.serviceLevel, unitsFromA=cell.unitsFromA,
                           unitsFromB=cell.unitsFromB) for cell in cells],
    )
    contract = snapshot.contract
    risk = RiskView(
        scenarioId=snapshot.scenario.id,
        sourceMode=snapshot.sourceMode,
        contractReview="PENDING_LOCAL_MOCK" if snapshot.sourceMode == "LOCAL_MOCK" else "HUMAN_APPROVED",
        matchedEvidenceIds=[item.id for item in snapshot.evidence if item.quoteMatched],
        demandShockPercent=snapshot.scenario.demandShock,
        leadTimeMultiplier=snapshot.scenario.leadTimeMultiplier,
        monteCarloRuns=snapshot.simulation.monteCarloRuns,
        contract=RiskContract(renewalLocked=contract.renewalLocked,
                              renewalNoticeDays=contract.renewalNoticeDays,
                              renewalTermMonths=contract.renewalTermMonths,
                              renewalPriceIncreasePct=contract.renewalPriceIncreasePct,
                              minPurchaseShareA=contract.minPurchaseShareA,
                              forecastBasis=contract.forecastBasis,
                              lockedForecastUnits24m=contract.lockedForecastUnits24m,
                              minPurchaseUnitsA=contract.minPurchaseUnitsA,
                              terminationFeeUsd=contract.terminationFeeUsd),
        options=[RiskOption(optionId=cell.optionId, feasible=cell.feasible,
                            cashOutflowP90Usd=cell.cashOutflowP90,
                            stockoutProbability=cell.stockoutProbability) for cell in cells],
    )
    return {"CFO": cfo, "COO": coo, "Risk": risk}


def allowed_refs(role: str, view: CfoView | CooView | RiskView) -> tuple[list[str], list[str]]:
    """Build refs from the concrete typed projection; never a hard-coded UI metric list."""
    if role == "CFO" and isinstance(view, CfoView):
        fields = ("expectedTcoUsd", "cashOutflowP90Usd", "deltaTcoUsd", "purchaseUsd", "holdingUsd",
                  "stockoutLossUsd", "renewalPremiumUsd", "terminationFeeUsd")
        return [f"{field}:{option.optionId}" for option in view.options for field in fields], []
    if role == "COO" and isinstance(view, CooView):
        fields = ("stockoutProbability", "serviceLevel", "unitsFromA", "unitsFromB")
        return ([f"{field}:{option.optionId}" for option in view.options for field in fields] +
                ["demandUnits24m", "leadTimeMultiplier"], [])
    if role == "Risk" and isinstance(view, RiskView):
        fields = ("renewalLocked", "renewalNoticeDays", "renewalTermMonths", "renewalPriceIncreasePct",
                  "minPurchaseShareA", "forecastBasis", "lockedForecastUnits24m", "minPurchaseUnitsA",
                  "terminationFeeUsd", "demandShockPercent", "leadTimeMultiplier", "monteCarloRuns")
        return ([f"cashOutflowP90Usd:{option.optionId}" for option in view.options] +
                [f"stockoutProbability:{option.optionId}" for option in view.options] + list(fields),
                list(view.matchedEvidenceIds))
    raise ValueError("Role and projection type do not match")
