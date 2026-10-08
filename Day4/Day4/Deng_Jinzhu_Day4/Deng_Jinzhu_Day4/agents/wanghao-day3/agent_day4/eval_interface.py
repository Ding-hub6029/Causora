"""Day5 evaluation boundary: no Day4 final held-out score, no label-file import."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
FORBIDDEN_KEYS={'label','labels','expected','expectedIssues','correctAnswer','severityLabel','ground_truth','answer','annotations'}


def _reject_labels(value,path=()):
    if isinstance(value,dict):
        forbidden=set(value)&FORBIDDEN_KEYS
        # These labels are frozen public DTO display names, not fault categories.
        if len(path)>=2 and path[-2]=='options' and isinstance(path[-1],int) and value.get('id') in ('D0','D1','D2') and 'shareA' in value and isinstance(value.get('terminateA'),bool):forbidden.discard('label')
        if path and path[-1]=='scenario' and value.get('id') in ('baseline','demand-drop','lead-stress') and 'demandShock' in value and 'demandUnits24m' in value:forbidden.discard('label')
        if forbidden:raise ValueError('Evaluation input contains answer/label fields')
        for key,part in value.items():_reject_labels(part,path+(key,))
    elif isinstance(value,list):
        for index,part in enumerate(value):_reject_labels(part,path+(index,))


def case_identifier(record):
    value=record.get('caseId',record.get('id'))
    if not isinstance(value,str) or not value:raise ValueError('Neutral case id required')
    return value


def load_blind_inputs(path:Path|str)->list[dict]:
    """Read only a supplied inputs JSONL, never a builder, labels or an oracle."""
    records=[]
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        record=json.loads(line)
        if not isinstance(record,dict):raise ValueError('Case object required')
        _reject_labels(record);case_identifier(record);records.append(record)
    if len({case_identifier(r) for r in records})!=len(records):raise ValueError('Duplicate case id')
    return records


def model_payload(record):
    """Reuse the existing safe model loader: input only, no IDs/metadata/labels."""
    _reject_labels(record)
    from agent_day3.evals.scoring import prompt_payload
    return prompt_payload(record)


def prediction_record(*,case_id:str,input_record:dict,issues:list[dict],provider:str,model:str,run_id:str,status='ok')->dict:
    _reject_labels(input_record)
    if case_identifier(input_record)!=case_id:raise ValueError('Case identity differs from frozen input')
    if status not in ('ok','timeout','error'):raise ValueError('Prediction execution status required')
    payload=json.dumps(input_record,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    if not all(isinstance(v,str) and v for v in (case_id,provider,model,run_id)):raise ValueError('Prediction provenance required')
    # Feed only scorerRow into the old scorer; keep provider/issue audit separate.
    scorer={'caseId':case_id,'inputSha256':hashlib.sha256(payload).hexdigest(),'status':status,'faultDetected':bool(issues) if status=='ok' else None}
    return {'caseId':case_id,'scorerRow':scorer,'issues':issues if status=='ok' else [],'provider':provider,'model':model,'runId':run_id,
            'evaluationStatus':'UNSCORED_HELDOUT_PREDICTION','humanLabelsApproved':False}
