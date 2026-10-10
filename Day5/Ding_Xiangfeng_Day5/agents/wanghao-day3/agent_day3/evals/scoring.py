"""Offline scoring infrastructure; never executes Critic or fabricates predictions."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def canonical(value):
    # Keep the input-only loader independent of the label-bearing generator.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def prompt_payload(record: dict):
    """Model-facing loader: no labels, opaque IDs, metadata or oracle file."""
    if set(record) != {'caseId','split','source','input'} or record['split'] != 'heldout':
        raise ValueError('Only input-only held-out records may enter the model loader')
    forbidden = {'expected','faulty','category','labelStatus','inputSha256','referenceReason'}
    def check(value):
        if isinstance(value,dict):
            if forbidden & set(value): raise ValueError('Answer-bearing field in model input')
            for v in value.values(): check(v)
        elif isinstance(value,list):
            for v in value: check(v)
    check(record['input'])
    return json.loads(canonical(record['input']))


def score(inputs: list, labels: list, predictions: list, *, draft_rehearsal: bool = False):
    """All rows required; timeouts count as missed faulty cases, not clean successes.

    Formal scoring requires separately reviewed labels. This Day3 archive supplies
    draft labels only. --draft-rehearsal is an explicit non-official harness test.
    """
    def index(rows):
        result={r['caseId']:r for r in rows}
        if len(result)!=len(rows): raise ValueError('Duplicate case ID')
        return result
    ins,labs,preds=index(inputs),index(labels),index(predictions)
    if set(ins)!=set(labs) or set(ins)!=set(preds):
        raise ValueError('Missing or extra cases; predictions must report every timeout explicitly')
    if not draft_rehearsal and any(r['labelStatus']!='INDEPENDENTLY_REVIEWED' for r in labels):
        raise ValueError('Day3 draft labels cannot produce an official held-out score')
    tp=fp=fn=tn=failed=0; clean_failed=0
    for ident,item in ins.items():
        prompt_payload(item)
        sha=hashlib.sha256(canonical(item)).hexdigest()
        label,pred=labs[ident],preds[ident]
        if label['inputSha256']!=sha or pred.get('inputSha256')!=sha:
            raise ValueError('Prediction/label is not bound to the locked input digest')
        if set(pred)!={'caseId','inputSha256','status','faultDetected'}:
            raise ValueError('Unexpected prediction fields')
        if pred['status'] not in ('ok','timeout','error'):
            raise ValueError('Unknown prediction status')
        expected=label['expected']['faulty']
        if type(expected) is not bool: raise ValueError('Label must be boolean')
        if pred['status']!='ok':
            if pred['faultDetected'] is not None: raise ValueError('Failed model call cannot fabricate a prediction')
            failed+=1
            if expected: fn+=1
            else: clean_failed+=1
            continue
        detected=pred['faultDetected']
        if type(detected) is not bool: raise ValueError('Prediction must be boolean')
        if detected and expected: tp+=1
        elif detected: fp+=1
        elif expected: fn+=1
        else: tn+=1
    return {'kind':'DRAFT_HARNESS_REHEARSAL_NOT_CRITIC_PERFORMANCE' if draft_rehearsal else 'CRITIC_EVALUATION',
        'status':'incomplete' if failed else 'complete','totalCases':len(ins),
        'truePositive':tp,'falsePositive':fp,'falseNegative':fn,'trueNegative':tn,
        'falsePositiveCount':fp,'failedCalls':failed,'failedCleanControls':clean_failed,
        'recall':tp/(tp+fn) if tp+fn else None,'precision':tp/(tp+fp) if tp+fp else None,
        'guardrailAndValidatorMode':'must_be_disabled_in_critic_runner',
        'caveat':'The scorer does not attest whether any provider ran, prompts were frozen, labels were human-reviewed, or the guards were disabled.'}


def main():
    p=argparse.ArgumentParser(description='Score locked Critic predictions offline; no model execution')
    p.add_argument('--inputs',type=Path,required=True); p.add_argument('--labels',type=Path,required=True)
    p.add_argument('--predictions',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--draft-rehearsal',action='store_true')
    a=p.parse_args()
    if a.output.exists(): raise FileExistsError('Do not overwrite a prior evaluation audit')
    result=score(read_jsonl(a.inputs),read_jsonl(a.labels),read_jsonl(a.predictions),draft_rehearsal=a.draft_rehearsal)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
