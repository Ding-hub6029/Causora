"""Code-bound allocation facts and targeted prose checks, never new simulation.

The concentration measure is the sum of squared planned supplier shares. It is
not market/portfolio diversification and is not exposed as a new public metric.
These fail-closed English checks are scoped regressions, not general entailment.
"""
from __future__ import annotations
import math
import re
from .wire import PipelineError
from .business import _A_RETENTION,_AVOID_EXIT,_EXIT_AVOIDED


GENERATION_RULES = (
    'Distinguish supplier identity from diversification. Terminating A and allocating all sourcing to B '
    'reduces dependence on A, NOT overall supplier concentration and NOT supplier diversification. '
    'Only when the selected option terminates A, explain its applicable fixed exit fee and B-only sourcing. '
    'When the selected option retains both A and B, describe mixed sourcing; do not claim B-only delivery '
    'characteristics, concentration in B, or an active termination fee for that selected mix. '
    'Do not claim risk elimination, a waived fee, a balanced A/B allocation or an unmet/met cash limit '
    'contrary to current supplied facts. Stockout probability is a computed scenario result, not a guess '
    'from the supplier name. A staged contingency playbook is not a staged change to option shares. '
    'Mixed retained-A alternatives and future mitigation must be explicitly distinguished from selected exit. '
    'Do not invent new suppliers, contractual releases or production approval.'
)


def allocation_facts(options):
    baseline=next(o for o in options if o['id']=='D0')
    base_hhi=float(baseline['shareA'])**2+(1-float(baseline['shareA']))**2
    facts={}
    for option in options:
        share=option['shareA']
        if isinstance(share,bool) or not isinstance(share,(int,float)) or not math.isfinite(share) or not 0<=share<=1:
            raise PipelineError('allocation_fact_invalid')
        if not isinstance(option['terminateA'],bool) or option['terminateA'] and share!=0:
            raise PipelineError('allocation_fact_invalid',details={'optionId':option['id'],'violations':['termination_with_retained_a_share']})
        hhi=share**2+(1-share)**2
        facts[option['id']]={'optionId':option['id'],'terminateA':option['terminateA'],'shareA':share,'shareB':1-share,
            'allSupplyFromB':share==0,'mixedSuppliers':0<share<1,'concentrationIndex':hhi,
            'baselineConcentrationIndex':base_hhi,'overallConcentrationLowerThanBaseline':hhi<base_hhi-1e-12,
            'dependenceOnALowerThanBaseline':share<baseline['shareA'],'singleSupplierDependence':share in (0,1)}
    return facts


def result_facts(run,scenario_id):
    facts=allocation_facts(run.simulation_request['options'])
    rows=run.simulation_response['data']['simulation']['matrix'][scenario_id]
    for row in rows:
        fact=facts[row['optionId']]
        expected_fee=run.contract['terminationFeeUsd'] if fact['terminateA'] and run.contract['renewalLocked'] else 0
        if row['breakdown']['terminationFee']!=expected_fee or fact['allSupplyFromB'] and row['unitsFromA']!=0:
            raise PipelineError('allocation_fact_invalid',details={'optionId':row['optionId'],'violations':['allocation_or_exit_fee_does_not_match_current_result']})
        fact.update(terminationFeeUsd=row['breakdown']['terminationFee'],stockoutProbability=row['stockoutProbability'],
            cashOutflowP90Usd=row['cashOutflowP90'],cashCeilingUsd=run.simulation_request['budgetCeilingUsd'],
            cashWithinCeiling=row['cashOutflowP90']<=run.simulation_request['budgetCeilingUsd'],
            stockoutRiskThreshold=run.simulation_request['riskThreshold'],stockoutWithinThreshold=row['stockoutProbability']<=run.simulation_request['riskThreshold'])
    return facts


_LOWER_CONCENTRATION=re.compile(r'\b(?:reduce\w*|lower\w*|decreas\w*|minimiz\w*|alleviat\w*|eliminat\w*)\b.{0,45}\b(?:concentration|concentrated\s+supply|single[- ]supplier\s+dependence)\b|\bconcentration\b.{0,40}\b(?:reduced|lower|decreased|improved|eliminated)\b',re.I)
_HIGHER_CONCENTRATION=re.compile(r"\b(?:increase\w*|raise\w*|higher|greater)\s+(?:(?:overall|supplier|vendor)\s+){0,2}concentration\b",re.I)
_DIVERSIFIED=re.compile(r'\b(?:diversif\w+|diversified|diverse\s+(?:supplier|supply|sourcing)|spread\w*\s+(?:supply|sourcing|supplier)\s+risk)\b',re.I)
_MIXED_ASSERTION=re.compile(r'\b(?:retains?|keeps?|maintains?|uses?|achieves?|creates?|provides?)\b.{0,30}\b(?:both\s+suppliers|balanced\s+(?:allocation|supplier|mix)|mixed\s+(?:supplier|allocation))\b',re.I)
_B_ONLY_ASSERTION=re.compile(r'\bb[-\u2010-\u2015 ]only\s+(?:sourc\w*|suppl\w*|allocat\w*|deliver\w*)|\b(?:all|entire|sole|exclusive)\s+(?:supply|sourcing|procurement)\s+(?:is\s+)?(?:from|with|to|in)\s+(?:supplier\s+)?b\b|\b(?:concentrat\w*\s+(?:supply\s+)?(?:in|with|on)\s+(?:supplier\s+)?b|supply\s+(?:is\s+|remains\s+)?concentrated\s+(?:in|with|on)\s+(?:supplier\s+)?b)\b',re.I)
_FEE_FREE=re.compile(r'\b(?:no|without|avoid\w*|waiv\w*|free\s+of)\b.{0,25}\b(?:exit|termination|contract\s+exit)\s+(?:fee|cost|charge)|\b(?:exit|termination)\s+(?:fee|cost|charge)\b.{0,25}\b(?:waived|absent|eliminated|not\s+(?:paid|required|included))\b|\b(?:fee[- ]free|cost[- ]free)\s+(?:exit|termination)\b',re.I)
_NO_STOCKOUT=re.compile(r'\b(?:no|zero|without|eliminat\w*|remov\w*)\b.{0,22}\b(?:stockout|shortage|delivery\s+risk)|\b(?:stockout|shortage)\s+(?:risk|probability|likelihood)\b.{0,16}\b(?:zero|eliminated|absent|removed)|\b(?:stockout[- ]free|risk[- ]free\s+supply|guarantee\w*\s+(?:uninterrupted\s+supply|delivery\s+continuity))\b',re.I)
_HIGH_STOCKOUT=re.compile(r'\b(?:high|extreme|certain|severe)\s+(?:stockout|shortage)\s+(?:risk|probability|likelihood)\b',re.I)
_CASH_BREACH=re.compile(r'\b(?:exceed\w*|breach\w*|violat\w*)\b.{0,25}\b(?:cash|budget|treasury)\s+(?:ceiling|cap|limit)|\b(?:cash|budget|treasury)\s+(?:ceiling|cap|limit)\b.{0,20}\b(?:exceeded|breached|violated)\b',re.I)
_CASH_WITHIN=re.compile(r'\b(?:within|below|under|meets?|satisfies|complies\s+with)\b.{0,20}\b(?:cash|budget|treasury)\s+(?:ceiling|cap|limit)\b',re.I)
_NEGATION=re.compile(r'\b(?:not|never|no|without|cannot|doesn.t|does\s+not|must\s+not|do\s+not|should\s+not|avoid\s+claiming|rather\s+than)\b.{0,70}$',re.I)
_FUTURE=re.compile(r'\b(?:consider|monitor|manage|mitigate|must\s+avoid|should\s+avoid|could\s+exceed|may\s+exceed)\b|\b(?:future|further|additional|contingency)\b.{0,40}\b(?:plan|planning|mitigation|scope|measure|supplier|supply)\b',re.I)


def _asserted(pattern,clause):
    for match in pattern.finditer(clause):
        prefix=clause[max(0,match.start()-65):match.start()]
        # Acknowledging an exit fee instead of a waived fee is not a waiver claim.
        if pattern is _FEE_FREE and re.match(r"(?:exit|termination)\s+(?:fee|cost|charge)\b", match.group(), re.I) and re.search(r"\b(?:instead of|rather than)\b", match.group(), re.I):
            continue
        if _NEGATION.search(prefix):continue
        if _FUTURE.search(prefix):continue
        yield match


def check_prose(text,*,facts,default_option_id,stage):
    """Verify affirmative assertions; permit negated warnings/future mitigation."""
    violations=[]
    clauses=[]
    for sentence in re.split(r'[.!?;]',text):
        # Keep explicit conditional-alternative scope across "but/while" clauses.
        # Without this, a correct warning about an alternative all-B exit can be
        # misread as a claim about the selected mixed plan after the conjunction.
        exit_alternative=bool(re.search(r'\b(?:all[-\u2010-\u2015 ]b(?:\s+exit)?|b[-\u2010-\u2015 ]only|exit|terminat\w*)\b.{0,95}\balternative\b',sentence,re.I)
            and re.search(r'\b(?:conditional|hypothetical|separate|would|could|if)\b',sentence,re.I))
        for part in re.split(r'\b(?:but|whereas|however|while|yet)\b',sentence,flags=re.I):
            clauses.append((part,exit_alternative))
    for clause,exit_alternative in clauses:
        if not clause.strip():continue
        explicit=re.findall(r'\bD[012]\b',clause)
        oid=explicit[0] if len(set(explicit))==1 else default_option_id
        # Mixed-alternative commentary must not be misattributed to selected B-only.
        if not explicit and re.search(r'\b(?:mixed[- ]allocation\s+alternative|rebalancing\s+alternative|retained[- ]a\s+alternative)\b',clause,re.I):
            mixed=[key for key,value in facts.items() if value['mixedSuppliers']]
            if len(mixed)==1:oid=mixed[0]
        # A named hypothetical all-B exit is an alternative, not a claim about
        # the selected mixed plan. A bare B-only assertion remains selected-bound.
        if not explicit and (exit_alternative or re.search(r'\b(?:all[-\u2010-\u2015 ]b|b[-\u2010-\u2015 ]only|exit|terminating)\s+alternative\b',clause,re.I)):
            exits=[key for key,value in facts.items() if value['terminateA'] and value['allSupplyFromB']]
            if len(exits)==1:oid=exits[0]
        fact=facts[oid]
        for match in _asserted(_LOWER_CONCENTRATION,clause):
            if re.search(r'\b(?:not|rather\s+than)\b',match.group(),re.I):continue
            if not fact['overallConcentrationLowerThanBaseline']:
                violations.append('unsupported_overall_concentration_reduction')
        if fact['concentrationIndex'] <= fact['baselineConcentrationIndex'] + 1e-12 and any(_asserted(_HIGHER_CONCENTRATION,clause)):
            violations.append('unsupported_overall_concentration_increase')
        if not fact['mixedSuppliers'] and any(_asserted(_DIVERSIFIED,clause)):
            violations.append('unsupported_supplier_diversification')
        if fact['allSupplyFromB'] and any(_asserted(_MIXED_ASSERTION,clause)):
            violations.append('b_only_described_as_mixed_allocation')
        hypothetical_exit_qualifier=re.search(r'\bfor\s+(?:any\s+|a\s+)?(?:conditional|hypothetical)\s+(?:all[-\u2010-\u2015 ]b\s+|b[-\u2010-\u2015 ]only\s+)?exit\b',clause,re.I)
        portion_qualifier=re.search(r'\bfor\s+(?:the|that)\s+portion\s+(?:moved|shifted|allocated)\b',clause,re.I)
        b_only_claims=[match for match in _asserted(_B_ONLY_ASSERTION,clause)
            if not (portion_qualifier and re.search(r'concentrat',match.group(),re.I))]
        if fact['mixedSuppliers'] and not hypothetical_exit_qualifier and b_only_claims:
            violations.append('mixed_allocation_described_as_b_only')
        conditional_retention = re.search(r'\bretained(?:[- ]a)?\s+alternatives?\b', clause, re.I) and re.search(r'\b(?:conditional|would|not active|separate)\b', clause, re.I)
        if fact['terminateA'] and not conditional_retention and any(_asserted(_A_RETENTION,clause)):
            violations.append('terminated_supplier_a_retained')
        if fact['terminateA'] and (any(_asserted(_AVOID_EXIT,clause)) or any(_asserted(_EXIT_AVOIDED,clause))):
            violations.append('termination_described_as_avoiding_exit')
        if fact['terminationFeeUsd']>0 and any(_asserted(_FEE_FREE,clause)):
            violations.append('applicable_exit_fee_denied')
        if fact['stockoutProbability']>0 and any(_asserted(_NO_STOCKOUT,clause)):
            violations.append('computed_stockout_risk_denied')
        if fact['stockoutProbability']==0 and any(_asserted(_HIGH_STOCKOUT,clause)):
            violations.append('unsupported_high_stockout_risk')
        if fact['cashWithinCeiling'] and any(_asserted(_CASH_BREACH,clause)):
            violations.append('computed_cash_compliance_denied')
        if not fact['cashWithinCeiling'] and any(_asserted(_CASH_WITHIN,clause)):
            violations.append('computed_cash_breach_denied')
    if violations:raise PipelineError('business_semantic_contradiction',details={'stage':stage,'violations':sorted(set(violations))})
    return {'allocationSource':'CURRENT_REQUEST_AND_VERIFIED_MC_ROW','overallConcentrationIndexCompared':True,'riskAndFeeAssertionsChecked':True}


def terminating_brief(option_fact):
    """Safe code-generated fallback explanation if the model challenges selection."""
    fee='account for the applicable fixed exit fee' if option_fact['terminationFeeUsd']>0 else 'confirm the modeled exit-cost treatment'
    return ('Terminate supplier A and move procurement to supplier B, pending human review.',
        'This reduces dependence on A, not overall supplier concentration or supplier diversification. '
        f'The sourcing plan remains concentrated in B; {fee} and evaluate B delivery and computed shortage risk within the existing cash and risk constraints.')


def check_required_exit_explanation(value,*,fact):
    """Require the critical tradeoff in the actual published terminating brief."""
    if not (fact['terminateA'] and fact['allSupplyFromB']):return
    text=value.recommendation+' '+value.rationale
    missing=[]
    if not re.search(r'\b(?:dependence|dependency|reliance|exposure)\s+(?:on|to)\s+(?:supplier\s+)?a\b',text,re.I):missing.append('a_dependence_not_distinguished')
    if not re.search(r'\b(?:b[- ]only|supplier\s+b\s+(?:concentration|dependence)|concentrat\w*\s+(?:in|on)\s+(?:supplier\s+)?b|dependen\w*\s+on\s+(?:supplier\s+)?b|(?:sole|exclusive)\s+(?:supply|source|supplier)\s+(?:from|is)\s+(?:supplier\s+)?b)\b',text,re.I):missing.append('b_supply_concentration_not_explained')
    if fact['terminationFeeUsd']>0 and not re.search(r'\b(?:exit|termination)\s+(?:fee|cost|charge)\b',text,re.I):missing.append('applicable_exit_fee_omitted')
    if not re.search(r'\b(?:delivery\s+risk|shortage|stockout|supply\s+continuity|replacement\s+supply|delivery\s+reliability)\b',text,re.I):missing.append('b_delivery_or_shortage_risk_omitted')
    if missing:raise PipelineError('business_semantic_contradiction',details={'stage':'Synthesizer','violations':missing})
