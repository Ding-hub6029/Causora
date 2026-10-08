"""TEST_FIXTURE_ONLY helpers. Never imported by runtime providers/adapters."""
import asyncio,copy,json
from pathlib import Path
from agent_day4.inputs import VerifiedRun

ROOT=Path(__file__).resolve().parents[3]
BACKEND=ROOT/'backend/backend'


def reviewed_run():
    from agent_day4.evidence import enrich_evidence
    fixture=json.loads((ROOT/'frontend/tests/fixtures/reviewed-v2-TEST_FIXTURE_ONLY.json').read_text(encoding='utf-8'))
    contract=json.loads((BACKEND/'reviewed/wang-2026-10-07/reviewed_contract.json').read_text(encoding='utf-8'))['contract']
    evidence=json.loads((BACKEND/'demo_data/causora_day1_mock.json').read_text(encoding='utf-8'))['evidence']
    renewal=next(e for e in evidence if e['id']=='EV-019')
    evidence.append({**renewal,'id':'EV-020','extractedField':'auto_renew','extractedValue':True,'locatorBbox':None})
    enriched=enrich_evidence(evidence,source_root=BACKEND,contract=contract)
    return VerifiedRun(fixture['request'],fixture['response'],contract,tuple(enriched),BACKEND,fixture['response']['requestId'])


def boardroom_request(run,scenario='demand-drop'):
    s=run.simulation_response['data']['simulation']
    return {'schemaVersion':'causora.contract.v1','simulationId':s['simulationId'],'dataVersion':s['dataVersion'],'scenarioId':scenario}

class FixtureProvider:
    kind='TEST_FIXTURE_ONLY'
    model='TEST_FIXTURE_ONLY-gpt';family='openai-gpt'
    def __init__(self,*,delay=0.01,failures=None,mutations=None):
        self.delay=delay;self.failures=failures or {};self.mutations=mutations or {};self.events=[];self.active=0;self.max_active=0;self.cancellations=[]
    async def complete(self,*,stage,payload,schema,system):
        self.events.append((stage,copy.deepcopy(payload)));self.active+=1;self.max_active=max(self.max_active,self.active)
        try:
            await asyncio.sleep(self.delay)
            if stage in self.failures:
                error=self.failures[stage]
                if callable(error):error=error()
                raise error
            if stage in ('CFO','COO','Risk'):
                output={'role':stage,'headline':'Review the current tradeoffs','body':'Review the referenced current-run metrics.',
                    'status':'Watch','metric_refs':payload['allowedMetricRefs'],'evidence_ids':payload['allowedEvidenceIds'][:1],
                    'option_ids':payload['allowedOptionIds'],'claims':[]}
            elif stage=='Critic':
                output={'cash_ceiling_enforced':True,'checked_roles':['CFO','COO','Risk'],'coverage':['renewal_condition','locked_forecast','minimum_commitment','demand_change','cash_pressure','holding_cost','omission','conflict'],
                    'issues':[{'kind':'compound_risk','severity':'High','headline':'Locked commitments interact with reduced demand',
                    'body':'The financial view omits the joint effect of fixed forecast commitments and reduced demand. Cash exposure must be assessed together with inventory carrying costs, without attributing every holding delta to the contract.',
                    'evidence_ids':['EV-024','EV-014'],'claims':[],'roles':['CFO','COO','Risk']}]}
            else:
                action=payload['verifiedBusinessFacts']['selectedAction']
                output={'option_id':payload['serverSelectedOptionId'],'option_action':action,'cash_ceiling_enforced':True,
                    'recommendation':'Terminate supplier A and move procurement to supplier B.' if action=='terminate_supplier_a' else 'Use the verified selected option for human review.',
                    'rationale':('This reduces dependence on A, not overall supplier concentration. Supply is concentrated in B; account for the fixed exit fee and monitor B delivery risk and computed shortage likelihood under the existing cash ceiling.' if action=='terminate_supplier_a' else 'The selected alternative follows the existing cash ceiling checks and accounts for its sourcing action.'),
                    'metric_refs':['delta_tco','stockout_probability','cash_outflow_p90'],'claims':[],'challenges':[]}
            mutation=self.mutations.get(stage)
            if mutation:output=mutation(copy.deepcopy(output))
            return output
        except asyncio.CancelledError:self.cancellations.append(stage);raise
        finally:self.active-=1
