import pytest
from agent_day3.dev_roles import response_schema,ClaimSelection


def test_remote_strict_schema_omits_unsupported_uniqueitems():
    schema=response_schema('CFO',['cfo_cost_components_bound'])
    assert 'uniqueItems' not in schema['properties']['claim_ids']
    assert schema['additionalProperties'] is False
    assert set(schema['properties'])=={'role','claim_ids','status'}


def test_duplicate_claims_still_rejected_locally():
    with pytest.raises(ValueError):
        ClaimSelection.model_validate({'role':'CFO','claim_ids':['cfo_cost_components_bound']*2,'status':'Watch'})
