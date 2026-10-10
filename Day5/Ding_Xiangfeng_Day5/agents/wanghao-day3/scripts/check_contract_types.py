"""Generate compile-time checks from actual emitted JSON; no frontend edits/build."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def main():
    mock=json.loads((ROOT/'fixtures/causora_day1_mock.json').read_text(encoding='utf-8'))
    candidate=json.loads((ROOT/'evidence_review/data/reviewed_data.json').read_text(encoding='utf-8'))
    draft=json.loads((ROOT/'agent_day3/examples/frontend_agent_draft_local_mock.json').read_text(encoding='utf-8'))
    examples=[('simulation',mock['simulation'],'SimulationResult'),
              ('scenarios',mock['scenarios'],'Scenario[]'),
              ('options',mock['options'],'DecisionOption[]'),
              ('contractInputs',{k:candidate[k] for k in ('contract','evidence','variables')},
               'Pick<DatasetResult, "contract" | "evidence" | "variables">'),
              ('agentOutputs',draft['agentOutputs'],'AgentOutput[]')]
    text='// Generated from actual artifacts; checked against the unchanged Ding Day3 contract.\n'
    text+='import type { SimulationResult, Scenario, DecisionOption, DatasetResult, AgentOutput } from "../reference/contracts";\n'
    for name,data,kind in examples:
        text+='export const '+name+' = '+json.dumps(data,ensure_ascii=False,indent=2)+' satisfies '+kind+';\n'
    out=ROOT/'reports/contract_examples.ts'
    out.write_text(text,encoding='utf-8')
    print(out)

if __name__=='__main__': main()
