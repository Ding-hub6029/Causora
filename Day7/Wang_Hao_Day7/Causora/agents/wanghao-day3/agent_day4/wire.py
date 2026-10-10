"""Internal schemas; public Boardroom DTOs remain frozen and are adapted in code."""
from __future__ import annotations
import copy
from dataclasses import dataclass,field
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,Field

ROLES=('CFO','COO','Risk')
TOKENS=('delta_tco','stockout_probability','cash_outflow_p90')
ROLE_TOKENS={'CFO':{'delta_tco','cash_outflow_p90'},'COO':{'stockout_probability'},'Risk':{'stockout_probability','cash_outflow_p90'}}

class PipelineError(ValueError):
    def __init__(self,reason:str,message:str='The AI review could not produce a validated result.',*,status:int=422,retryable:bool=False,details:dict|None=None):
        super().__init__(message);self.reason=reason;self.message=message;self.status=status;self.retryable=retryable;self.details=details or {}

@dataclass(frozen=True)
class PipelineConfig:
    total_timeout:float=110.0
    stage_timeout:float=30.0
    critic_timeout:float=35.0
    retries:int=1
    max_calls:int=10
    def __post_init__(self):
        if not 0<self.total_timeout<=120 or not 0<self.stage_timeout<=45 or not 0<self.critic_timeout<=45:
            raise ValueError('Bounded timeouts must stay below the frontend request deadline')
        if not 0<=self.retries<=1 or not 5<=self.max_calls<=12:raise ValueError('Finite retry/call bounds required')

@dataclass(frozen=True)
class PipelineResult:
    envelope:dict[str,Any]
    headers:dict[str,str]
    audit:dict[str,Any]=field(default_factory=dict)

class StrictModel(BaseModel):
    model_config=ConfigDict(strict=True,extra='forbid')

class Claim(StrictModel):
    field:Literal['headline','body','recommendation','rationale','challenges']
    start:int=Field(ge=0)
    end:int=Field(gt=0)
    ref:str

class RoleDraft(StrictModel):
    role:Literal['CFO','COO','Risk']
    headline:str=Field(min_length=1,max_length=180)
    body:str=Field(min_length=1,max_length=1200,description='Use current role-specific facts and selected allocation. Mixed A/B sourcing is not B-only. Only an actual exit to B reduces dependence on A without overall diversification; discuss exit costs only when applicable.')
    status:Literal['Aligned','Watch']
    metric_refs:list[str]=Field(min_length=1,max_length=8,description='Bare identifiers from allowedMetricRefs. Never use double-brace body placeholders in this array.')
    evidence_ids:list[str]=Field(max_length=6)
    option_ids:list[str]=Field(min_length=1,max_length=3)
    claims:list[Claim]=Field(max_length=24)

class IssueDraft(StrictModel):
    kind:Literal['compound_risk','omission','conflict']
    severity:Literal['High','Medium','Low']
    headline:str=Field(min_length=1,max_length=180,description='Qualitative heading. No digits, identifiers or numerical words. Say a sourcing alternative, never one option.')
    body:str=Field(min_length=1,max_length=1600,description='Independent qualitative reasoning tied to actual option allocation, fee, cash and stockout results. B-only is concentrated in B, not diversified. NO numbers or number words; IDs only in evidence_ids/roles; claims empty.')
    evidence_ids:list[str]=Field(max_length=6)
    claims:list[Claim]=Field(max_length=32)
    roles:list[Literal['CFO','COO','Risk']]=Field(min_length=1,max_length=3)

class CriticDraft(StrictModel):
    cash_ceiling_enforced:Literal[True]=Field(description='The supplied simulation already enforces cashOutflowP90 against its cash ceiling. Acknowledge the existing rule; never claim that it is absent.')
    issues:list[IssueDraft]=Field(max_length=8)
    checked_roles:list[Literal['CFO','COO','Risk']]=Field(min_length=3,max_length=3)
    coverage:list[Literal['renewal_condition','locked_forecast','minimum_commitment','demand_change','cash_pressure','holding_cost','omission','conflict']]=Field(min_length=8,max_length=8)

class SynthesisDraft(StrictModel):
    option_id:str
    option_action:Literal['retain_supplier_a','rebalance_suppliers','terminate_supplier_a']=Field(description='Exact action of option_id from supplied option definitions; termination must never be described as avoiding exit, retention, or gradual supplier-share adjustment.')
    cash_ceiling_enforced:Literal[True]=Field(description='The simulation selection already enforces a cash ceiling. This is an existing rule, not a missing guardrail.')
    recommendation:str=Field(min_length=1,max_length=500,description='English qualitative recommendation. Never use digits or numeric words, even one time or one-time. Say fixed contract exit fee instead.')
    rationale:str=Field(min_length=1,max_length=1400,description='For exit to B: distinguish reduced dependence on A from overall concentration, explicitly mention concentrated supply in B, applicable fixed exit fee and delivery/shortage risk. Respect current cash ceiling and computed risk. No claims of diversification for B-only. Never one time, one-time, first, second or any quantity.')
    metric_refs:list[str]=Field(min_length=1,max_length=8)
    claims:list[Claim]=Field(max_length=24)
    challenges:list[str]=Field(max_length=4)


def provider_schema(model:type[BaseModel])->dict:
    schema=model.model_json_schema()
    definitions=schema.pop('$defs',{})
    def inline(value,trail=()):
        if isinstance(value,dict):
            if '$ref' in value:
                ref=value['$ref'];name=ref.removeprefix('#/$defs/')
                if not ref.startswith('#/$defs/') or name not in definitions or name in trail:raise ValueError('Unsupported recursive/provider schema reference')
                return inline({**copy.deepcopy(definitions[name]),**{k:v for k,v in value.items() if k!='$ref'}},(*trail,name))
            return {key:inline(child,trail) for key,child in value.items()}
        if isinstance(value,list):return [inline(child,trail) for child in value]
        return value
    schema=inline(schema)
    # OpenAI strict schemas require every property in required, including arrays.
    def walk(value):
        if isinstance(value,dict):
            if value.get('type')=='object':
                value['additionalProperties']=False;value['required']=list(value.get('properties',{}))
            for part in value.values():walk(part)
        elif isinstance(value,list):
            for part in value:walk(part)
    walk(schema);return schema
