import asyncio
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from agent_day3.orchestrator import run_parallel
from agent_day3.provider import OfflineStubProvider
from agent_day3.projections import verify_human_review_bundle
from agent_day3.wire_models import DecisionOption, ContractConstraint, RealSnapshotInput, sha256_json
from agent_day3.tests.test_day3 import local_snapshot, real_payload, review_bundle


def test_metric_ref_must_belong_to_declared_option():
    class Bad(OfflineStubProvider):
        async def complete(self,**kwargs):
            value=await super().complete(**kwargs)
            if kwargs['role']=='CFO':
                value['option_ids']=['D0']; value['metric_refs']=['expectedTcoUsd:D2']
            return value
    run=asyncio.run(run_parallel(local_snapshot(),provider=Bad()))
    assert run.state=='PARTIAL' and run.outputs[0].failure=='invalid_response'


def test_provider_cannot_expand_validation_allowlist():
    class Bad(OfflineStubProvider):
        async def complete(self,**kwargs):
            value=await super().complete(**kwargs)
            if kwargs['role']=='COO':
                kwargs['payload']['allowedMetricRefs'].append('expectedTcoUsd:D0')
                kwargs['schema']['properties']['metric_refs']['items']['enum'].append('expectedTcoUsd:D0')
                value['metric_refs']=['expectedTcoUsd:D0']
            return value
    run=asyncio.run(run_parallel(local_snapshot(),provider=Bad()))
    assert run.outputs[1].failure=='invalid_response'


def test_async_verifier_is_not_silently_accepted(tmp_path):
    local=local_snapshot(); real=RealSnapshotInput.model_validate(real_payload(local)).to_boardroom_snapshot()
    async def unawaited(_): raise RuntimeError('This must not be skipped')
    with pytest.raises(ValueError,match='synchronous'):
        asyncio.run(run_parallel(real,provider=OfflineStubProvider(),review_bundle=review_bundle(tmp_path,local),simulation_verifier=unawaited))


def test_mutating_verifier_is_rejected_and_caller_input_unchanged(tmp_path):
    local=local_snapshot(); real=RealSnapshotInput.model_validate(real_payload(local)).to_boardroom_snapshot()
    before=real.model_dump_json()
    def mutate(snapshot): snapshot.simulation.matrix['demand-drop'].clear()
    with pytest.raises(ValueError,match='mutated'):
        asyncio.run(run_parallel(real,provider=OfflineStubProvider(),review_bundle=review_bundle(tmp_path,local),simulation_verifier=mutate))
    assert real.model_dump_json()==before


def test_receipt_must_include_exact_internal_auto_renew_id(tmp_path):
    bundle=review_bundle(tmp_path,local_snapshot())
    path=bundle/'human_receipt.json'; value=json.loads(path.read_text(encoding='utf-8'))
    value['approvedEvidenceIds'][-1]='EV-999'
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ValueError,match='six'): verify_human_review_bundle(bundle)


def test_mock_simulation_id_cannot_be_relabelled(tmp_path):
    local=local_snapshot(); value=real_payload(local)
    value['simulation']['simulationId']=local.simulation.simulationId
    value['reference']['simulationId']=local.simulation.simulationId
    value['reference']['simulationSha256']=sha256_json(value['simulation'])
    value['reference']['snapshotSha256']=sha256_json({k:v for k,v in value.items() if k!='reference'})
    real=RealSnapshotInput.model_validate(value).to_boardroom_snapshot()
    with pytest.raises(ValueError,match='relabelled'):
        asyncio.run(run_parallel(real,provider=OfflineStubProvider(),review_bundle=review_bundle(tmp_path,local),simulation_verifier=lambda _:None))


def test_semantic_hash_matches_integer_and_decimal_wire_numbers():
    assert sha256_json({'a':0,'b':[12,0.14]})==sha256_json({'a':0.0,'b':[12.0,0.14]})
    assert sha256_json({'a':False})!=sha256_json({'a':0})


def test_fixed_option_and_conditional_contract_state():
    local=local_snapshot()
    option=local.options[1].model_dump(mode='json'); option['shareA']=0.5
    with pytest.raises(ValidationError,match='fixed allocation'): DecisionOption.model_validate(option)
    contract=local.contract.model_dump(mode='json'); contract['renewalLocked']=False
    with pytest.raises(ValidationError,match='renewalLocked'): ContractConstraint.model_validate(contract)


def test_direct_real_snapshot_detects_modified_scenario():
    from agent_day3.models import BoardroomSnapshot
    real=RealSnapshotInput.model_validate(real_payload(local_snapshot())).to_boardroom_snapshot()
    payload=real.model_dump(mode='json'); payload['scenario']['demandShock']=-10
    with pytest.raises(ValidationError,match='full-input hash'): BoardroomSnapshot.model_validate(payload)


def test_other_matrix_scenario_also_needs_all_options():
    from agent_day3.wire_models import SimulationResult
    payload=local_snapshot().simulation.model_dump(mode='json')
    payload['matrix']['baseline'].pop()
    with pytest.raises(ValidationError,match='all three'): SimulationResult.model_validate(payload)


def test_internal_metadata_assembled_without_new_shared_fields(tmp_path):
    from agent_day3.integration import from_shared_records
    from agent_day3.wire_models import DatasetSuccessEnvelope
    real=RealSnapshotInput.model_validate(real_payload(local_snapshot()))
    bundle=review_bundle(tmp_path,local_snapshot())
    dataset=DatasetSuccessEnvelope.model_validate_json((bundle/'dataset_success.json').read_text(encoding='utf-8'))
    before=real.simulation.model_dump_json()
    assembled=from_shared_records(dataset=dataset,scenario=real.scenario,options=real.options,
        simulation=real.simulation,selection=real.selection,risk_threshold=0.12,budget_ceiling_usd=480000)
    assert assembled.simulation.model_dump_json()==before
    assert set(assembled.simulation.model_dump())==set(real.simulation.model_dump())
    assert assembled.reference.datasetId==dataset.data.datasetId
    assert assembled.to_boardroom_snapshot().sourceMode=='SIMULATION_READY'
    # This is shape assembly only; run_parallel still requires human and engine gates.
