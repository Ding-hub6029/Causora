"""Targeted business-fact consistency, distinct from Numeric Scan.

These checks cover known action/constraint contradictions; they are not a claim
of general natural-language entailment or final business-quality approval.
"""
from __future__ import annotations
import re
from .wire import PipelineError


def action_for(option:dict)->str:
    if option['terminateA'] is True:return 'terminate_supplier_a'
    return 'retain_supplier_a' if option['shareA']==1 else 'rebalance_suppliers'


def facts_for(run,scenario_id:str)->dict:
    data=run.simulation_response['data'];selection=data['selections'][scenario_id]
    chosen=selection['recommendedOptionId'];option=next(o for o in run.simulation_request['options'] if o['id']==chosen)
    row=next(r for r in data['simulation']['matrix'][scenario_id] if r['optionId']==chosen)
    ceiling=run.simulation_request['budgetCeilingUsd']
    return {'selectedOptionId':chosen,'selectedAction':action_for(option),'selectedShareA':option['shareA'],
        'terminationFeeUsd':row['breakdown']['terminationFee'],
        'cashCeilingRule':{'exists':True,'enforced':True,'metric':'cashOutflowP90','ceilingUsd':ceiling,
            'selectedCashOutflowP90Usd':row['cashOutflowP90'],'selectedWithinCeiling':row['cashOutflowP90']<=ceiling},
        'selectionConstraintViolations':list(selection['constraintViolations']),
        'notice':'Existing computed checks are not missing. Optional organizational escalation is a separate recommendation.'}


_CASH=r'(?:cash|treasury|budget|financial).{0,35}(?:ceiling|cap\b|limit|upper bound|guardrail|constraint|rule)'
_CASH_DENIAL=[
    re.compile(r'\b(?:no|lacks?|missing|absent)\b.{0,60}'+_CASH,re.I),
    re.compile(r'\bwithout\s+(?:(?:an?|any|existing|enforced|explicit|computational)\s+){0,3}'+_CASH,re.I),
    re.compile(_CASH+r'.{0,55}\b(?:missing|absent|not enforced|not checked|not applied|does not exist|is not enforced|are not enforced)\b',re.I),
    re.compile(r'\b(?:cannot|can\s*not|does not|do not|fails? to)\s+(?:check|enforce|apply|respect)\b.{0,70}(?:cash|treasury|budget|upper bounds?)',re.I),
    re.compile(r'\b(?:no|missing|absent)\b.{0,50}(?:rule|trigger|check).{0,100}(?:cash|treasury|budget)\b',re.I),
]


def check_cash_prose(text:str,*,stage:str):
    for sentence in re.split(r'[.!?]\s*',text):
        if re.search(r'\b(?:no|not)\s+(?:missing|absent)\s+(?:cash|treasury|budget)',sentence,re.I):continue
        for pattern in _CASH_DENIAL:
            match=pattern.search(sentence)
            if match:
                prefix=sentence[max(0,match.start()-35):match.start()]
                if re.search(r'(?:not true that|must not claim|never claim|do not claim)\s*$',prefix,re.I):continue
                raise PipelineError('business_semantic_contradiction',details={'stage':stage,'violations':['existing_cash_ceiling_denied']})


_AVOID_EXIT=re.compile(r'\b(?:avoids?|avoidance|prevent[s]?|eliminat(?:e[sd]?|ing)|without|no|minimi[sz](?:e[sd]?|ing))\b.{0,65}\b(?:exit(?:s|ing)?|terminat(?:e[sd]?|ion|ing))\b(?!\s+(?:fees?|costs?|charges?))',re.I)
_EXIT_AVOIDED=re.compile(r'\b(?:exit|termination)\b.{0,35}\b(?:avoided|unnecessary|not needed|not required)\b',re.I)
_STAGED_MIX=re.compile(r'\b(?:gradual(?:ly)?|staged|phased|progressive|stepwise|incremental|step-by-step)\b.{0,55}\b(?:suppliers?|sourcing|mix|shares?|allocation|rebalanc\w*)\b',re.I)
_MIX_STAGED=re.compile(r'\b(?:supplier\s+mix|supplier\s+shares?|sourcing\s+shares?|supplier\s+allocation)\b.{0,45}\b(?:gradual(?:ly)?|staged|phased|incremental)\b',re.I)
_POSITIVE_A_EXIT=re.compile(r'\b(?:terminat(?:e[sd]?|ing|ion)|exit(?:s|ing)?)\b.{0,45}\b(?:supplier\s+a|a\s+(?:supplier|contract)|contract\s+with\s+a)\b',re.I)
_A_RETENTION=re.compile(r'\b(?:retain[s]?|keep[s]?|maintain[s]?|continue[s]?|preserve[s]?|renew[s]?)\b.{0,40}\b(?:supplier\s+a|contract\s+with\s+a)\b',re.I)


def check_synthesis(value,options,*,stage='Synthesizer'):
    option=next(o for o in options if o['id']==value.option_id)
    action=action_for(option)
    violations=[]
    if value.option_action!=action:violations.append('option_action_mismatch')
    text=value.recommendation+' '+value.rationale
    check_cash_prose(text,stage=stage)
    if action=='terminate_supplier_a':
        if _AVOID_EXIT.search(text) or _EXIT_AVOIDED.search(text):violations.append('termination_described_as_avoiding_exit')
        if _STAGED_MIX.search(text) or _MIX_STAGED.search(text):violations.append('termination_described_as_staged_supplier_mix')
        exit_match=_POSITIVE_A_EXIT.search(text)
        if not exit_match:violations.append('supplier_a_termination_not_explained')
        elif re.search(r'\b(?:not|never|without)\b.{0,15}$',text[max(0,exit_match.start()-25):exit_match.start()],re.I):violations.append('supplier_a_termination_negated')
        for match in _A_RETENTION.finditer(text):
            if not re.search(r'\b(?:not|never|without|stop)\b.{0,15}$',text[max(0,match.start()-25):match.start()],re.I):violations.append('terminated_supplier_a_retained')
    if violations:raise PipelineError('business_semantic_contradiction',details={'stage':stage,'violations':sorted(set(violations))})
    for challenge in value.challenges:check_cash_prose(challenge,stage=stage+' challenge')
    return {'selectedAction':action,'cashCeilingEnforced':True,'checkedKnownContradictions':True}
