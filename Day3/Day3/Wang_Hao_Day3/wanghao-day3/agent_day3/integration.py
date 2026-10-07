"""Assemble Wang-internal metadata from unchanged shared v1 request/result records.

This creates hashes, NOT proof of computation. Human receipt and Jinzhu verifier
remain mandatory. No extra field is requested on SimulationResult or any endpoint.
"""
from __future__ import annotations
from .wire_models import (DatasetSuccessEnvelope,Scenario,DecisionOption,SimulationResult,
                          ScenarioSelection,RealSnapshotInput,sha256_json)


def from_shared_records(*, dataset: DatasetSuccessEnvelope, scenario: Scenario,
                        options: list[DecisionOption], simulation: SimulationResult,
                        selection: ScenarioSelection, risk_threshold: float,
                        budget_ceiling_usd: int) -> RealSnapshotInput:
    """Backend assembler: use the immutable /simulate request and response.

    dataset/contract/evidence: existing DatasetSuccess.
    scenario/options/limits: existing SimulateRequest record.
    simulation/selection: existing SimulateResponse record.
    The verifier must separately check those records against trusted engine state.
    """
    value={'schemaVersion':'causora.contract.v1','dataVersion':dataset.dataVersion,
           'scenario':scenario.model_dump(mode='json'),
           'options':[o.model_dump(mode='json') for o in options],
           'simulation':simulation.model_dump(mode='json'),
           'contract':dataset.data.contract.model_dump(mode='json'),
           'evidence':[e.model_dump(mode='json') for e in dataset.data.evidence],
           'selection':selection.model_dump(mode='json'),
           'selectionLimits':{'riskThreshold':risk_threshold,'budgetCeilingUsd':budget_ceiling_usd}}
    value['reference']={'schemaVersion':'causora.contract.v1','dataVersion':dataset.dataVersion,
        'datasetId':dataset.data.datasetId,'simulationId':simulation.simulationId,
        'scenarioId':scenario.id,'optionIds':[o.id for o in options],
        'simulationSha256':sha256_json(value['simulation']),
        'snapshotSha256':sha256_json(value)}
    return RealSnapshotInput.model_validate(value)
