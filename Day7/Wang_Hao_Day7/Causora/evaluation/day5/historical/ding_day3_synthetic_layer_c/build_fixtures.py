"""Synthetic layer-C draft corpus. Opaque held-out IDs and mixed order hide labels.
Facts are copied LOCAL MOCK, never engine output. Not a Critic result or oracle.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABEL_STATUS = 'AUTHOR_DRAFT_NEEDS_INDEPENDENT_REVIEW'
BASE = {
 'CFO': 'Compare total cost and cash exposure; purchase price alone does not settle a decision.',
 'COO': 'Use supplied service and stockout measures with purchased supplier allocation; the stress context matters.',
 'Risk': 'The notice condition, renewal uplift, fixed forecast floor and conditional exit obligation can affect downside.'}
SYNTHESIS = 'Keep finance, service and contract constraints together. A role comment is not final selection; only the engine selects among eligible options for the requested scenario. These are synthetic development inputs, not real supplier facts.'

# Scenario assignments are explicit. Labels/rationales never select input features.
# scenario, category, actor, statement, reference rationale
DEV = [
 ('baseline','omission','Synthesizer','Choose solely by purchase price; cash and service evidence need not influence the decision.','Synthesis explicitly discards finance and operations tradeoffs.'),
 ('lead-stress','conflict','COO','Keeping all purchases with the original supplier gives the best service in this stress case.','Mock service ordering contradicts this ordinal statement.'),
 ('demand-drop','compound_risk','Risk','Since demand fell, the committed forecast floor shrinks and cannot leave excess purchases.','The floor is locked, not rolling, and interacts with falling demand.'),
 ('baseline','conflict','CFO','Exit is the least expensive option in total cost here.','Same-scenario mock TCO does not place exit first.'),
 ('demand-drop','omission','Synthesizer','Evaluate the uplift but omit the fixed forecast purchasing term from the combined downside discussion.','A material Risk constraint is explicitly omitted.'),
 ('lead-stress','compound_risk','Synthesizer','Cheapest purchase price guarantees the best combined cash and service outcome during stress.','Price does not establish dominance across cash and continuity.'),
 ('baseline','conflict','Risk','The exit obligation cannot affect a decision during the renewed term.','The supplied obligation applies to renewed-term exit.'),
 ('demand-drop','omission','COO','Use realised demand as the sole purchased-allocation basis, ignoring the committed minimum.','Operations explicitly ignores an active purchasing constraint.')]
HELDOUT = [
 ('baseline','conflict','Synthesizer','Finance and Risk agree: diversification both improves and worsens cash headroom in the same comparison.','The supplied CFO/Risk statements explicitly contradict.'),
 ('baseline','omission','Synthesizer','Recommend exit on purchase economics without carrying forward the exit warning.','A specific Risk warning is discarded from the combined rationale.'),
 ('lead-stress','conflict','COO','The original-only supplier choice is safest for service and stockouts in this supplied stress matrix.','Original-only has the worst ordinal mock service/stockout position.'),
 ('baseline','omission','Synthesizer','Drop concentration from the conclusion although Operations flagged original-only allocation.','A stated operations concern is deliberately omitted.'),
 ('demand-drop','compound_risk','Risk','The higher renewal price and committed volume must never be considered together in demand downside.','Active price uplift and fixed volume jointly affect purchase exposure; no causal holding estimate is claimed.'),
 ('baseline','conflict','CFO','Moving fully to the replacement supplier removes every contractual exit-related financial consequence.','The renewed-term exit line remains positive for the exit option.'),
 ('lead-stress','omission','Synthesizer','Discard the service warning because purchase spending is already listed.','Listing spending does not resolve a continuity warning.'),
 ('demand-drop','compound_risk','CFO','Lower demand necessarily means every procurement plan spends less even with a fixed forecast commitment.','Committed procurement and lower realised demand interact; the universal claim is unsupported.'),
 ('baseline','conflict','Risk','Renewal is unlocked despite a decision after the deadline and no timely synthetic notice.','Date/register assumptions contradict the claimed configured state.'),
 ('baseline','omission','Synthesizer','Final exit downside includes only future unit prices, not the obligation Risk identified.','The explicit exit obligation is removed from the combined summary.'),
 ('baseline','conflict','COO','After exit all purchased units still go to the original supplier.','Structured exit allocation sends no units to the original supplier.'),
 ('demand-drop','compound_risk','COO','A fixed renewal forecast cannot make diversified purchased volume exceed realised demand.','Same-scenario diversified purchased volume exceeds mock demand.'),
 ('lead-stress','omission','Synthesizer','TCO ranking is enough for approval; ignore cash ceiling and service threshold.','The combined decision explicitly discards eligibility constraints.'),
 ('baseline','conflict','Risk','The quoted clause alone establishes that an actual supplier sent no notice.','Register is a separate synthetic source; this is an epistemic conflict, not a quote-match error.'),
 ('demand-drop','compound_risk','Synthesizer','The locked volume floor makes uplift irrelevant to purchase exposure under falling demand.','Committed quantity and uplift need joint assessment even when demand falls.'),
 ('demand-drop','omission','Synthesizer','Treat diversification as unconstrained; discard Risk minimum-purchase warning.','The provided purchasing floor is explicitly removed from synthesis.'),
 ('lead-stress','conflict','CFO','Greatest cash outflow also means most cash headroom under the same ceiling.','Cash-outflow/headroom ordinal directions are reversed.'),
 ('lead-stress','compound_risk','Synthesizer','Lower stockout risk alone guarantees replacement-only also passes the cash limit.','Better service coexists with excess mock cash outflow here.'),
 ('baseline','omission','Synthesizer','Retain the notice warning but suppress uplift and floor warnings in the final rationale.','Two stated material contract concerns are intentionally dropped.'),
 ('lead-stress','conflict','COO','Diversification cannot change stockout outcomes in this supplied matrix.','Same-scenario mock stockout values differ by allocation.')]
CLEAN = [
 ('baseline','Keep cost and service tradeoffs visible without forcing the cheapest purchase plan to win.'),
 ('lead-stress','Cash can disqualify an option even when its service is attractive.'),
 ('baseline','An exact quote does not establish real notice correspondence.'),
 ('demand-drop','Committed volume differs from realised demand; the forecast assumption is synthetic.'),
 ('lead-stress','Commentary is not a new simulation after an input edit.'),
 ('baseline','Notice language is conditional; earlier valid notice requires a new configured outcome.'),
 ('demand-drop','Uplift and minimum can interact, but mock holding aggregates do not prove causal inventory costs.'),
 ('lead-stress','Service alone does not establish dominance; retain cash and cost context.'),
 ('baseline','Exit cost applies conditionally to renewed-term exit, not every option.'),
 ('demand-drop','Purchased-unit split is fixed; these comparisons are illustrative, not stock-flow proof.')]


def canonical(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def packet(mock,scenario):
 return {'sourceMode':'LOCAL_MOCK','dataVersion':mock['meta']['dataVersion'],
  'simulationOrigin':'DING_FROZEN_ILLUSTRATIVE_MOCK_NOT_AN_ENGINE_RUN',
  'humanReviewStatus':'pending','realWorldVerification':'not_verified',
  'scenario':copy.deepcopy(next(s for s in mock['scenarios'] if s['id']==scenario)),
  'contract':copy.deepcopy(mock['contract']),'options':copy.deepcopy(mock['options']),
  'cells':copy.deepcopy(mock['simulation']['matrix'][scenario]),
  'baselineCells':copy.deepcopy(mock['simulation']['matrix']['baseline']),
  'evidence':copy.deepcopy(mock['evidence']),
  'selectionPolicy':{'riskThreshold':0.12,'budgetCeilingUsd':480000,
   'rule':'feasible AND stockout <= threshold AND cash <= ceiling; rank by TCO then ID'},
  'limitations':['Mock aggregates do not prove physical inventory causation.','Fixed forecast is synthetic, not a demand estimator.']}


def cases(split,mock):
 descriptions=[]
 for i,(scenario,category,actor,statement,reason) in enumerate(DEV if split=='dev' else HELDOUT):
  agents=dict(BASE); synthesis=SYNTHESIS
  if actor=='Synthesizer': synthesis=statement
  else: agents[actor]=statement
  if split=='heldout' and i==0:
   agents['CFO']='Diversification improves cash headroom in this comparison.'
   agents['Risk']='Diversification worsens cash headroom in this same comparison.'
  if split=='heldout' and i==3:
   agents['COO']+=' Original-only retains supplier concentration exposure.'
  if split=='heldout' and i in (1,9):
   agents['Risk']+=' The renewed-term exit obligation must be carried into an exit recommendation.'
  if split=='heldout' and i==6:
   agents['COO']+=' Original-only has the weakest mock service during this stress.'
  descriptions.append({'input':{'task':task(),'agents':agents,'synthesisDraft':synthesis,'frozenMockFacts':packet(mock,scenario)},
   'expected':{'faulty':True,'category':category,'reason':reason}})
 dev_clean=[
  ('baseline','Retain all stated concerns and leave the choice to eligible-option selection.'),
  ('lead-stress','The operations view reports continuity; finance reports cash, and both belong in synthesis.'),
  ('baseline','The separate correspondence record supports only the configured demonstration, not a real notice finding.'),
  ('demand-drop','Review the locked purchasing requirement together with demand contraction without claiming a real inventory forecast.')]
 for scenario,text in (dev_clean if split=='dev' else CLEAN):
  descriptions.append({'input':{'task':task(),'agents':dict(BASE),'synthesisDraft':SYNTHESIS+' '+text,'frozenMockFacts':packet(mock,scenario)},
   'expected':{'faulty':False,'category':None,'reason':None}})
 random.Random(731 if split=='dev' else 1943).shuffle(descriptions)
 for i,item in enumerate(descriptions,1):
  yield {'caseId':('d' if split=='dev' else 'h')+f'{i:03}','split':split,
   'source':'SYNTHETIC_LAYER_C_NOT_A_SIMULATION','labelStatus':LABEL_STATUS,**item}


def task():
 return 'Review the full discussion for material cross-role conflict, an explicitly discarded relevant concern, or a missed compound interaction. Do not penalize a role for lacking intentionally filtered fields. Do not credit arithmetic/quote validators or input-security checks.'


def build(folder:Path,root:Path=ROOT):
 mock=json.loads((root/'fixtures/causora_day1_mock.json').read_text(encoding='utf-8'))
 if mock['meta']['status']!='verified-local-mock': raise ValueError('Corpus must stay explicitly LOCAL MOCK')
 folder.mkdir(parents=True,exist_ok=True)
 dev=list(cases('dev',mock)); heldout=[]; labels=[]
 for case in cases('heldout',mock):
  entry={k:case[k] for k in ('caseId','split','source','input')}; heldout.append(entry)
  labels.append({'caseId':case['caseId'],'inputSha256':hashlib.sha256(canonical(entry)).hexdigest(),
   'labelStatus':LABEL_STATUS,'expected':case['expected']})
 for name,rows in [('critic_dev.jsonl',dev),('critic_heldout_inputs.jsonl',heldout),('critic_heldout_labels.jsonl',labels)]:
  (folder/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
 return dev,heldout,labels


if __name__=='__main__': build(Path(__file__).resolve().parent)
