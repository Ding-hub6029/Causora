"""Re-export the current internal/wire schemas; does not modify shared TypeScript."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent_day3.models import BoardroomSnapshot,CfoView,CooView,RiskView,ParallelRun
from agent_day3.adapter import Day3AgentDraft
from agent_day3.wire_models import RealSnapshotInput,HumanReceipt,ReviewScope,SimulationResult,DatasetSuccessEnvelope


def main():
    folder=ROOT/'agent_day3/schemas'
    for name,model in [('snapshot',BoardroomSnapshot),('cfo',CfoView),('coo',CooView),('risk',RiskView),
                       ('parallel_run',ParallelRun),('frontend_draft',Day3AgentDraft),
                       ('real_snapshot_input',RealSnapshotInput),('human_receipt',HumanReceipt),
                       ('review_scope',ReviewScope),('simulation_result',SimulationResult),
                       ('dataset_success',DatasetSuccessEnvelope)]:
        (folder/f'{name}.schema.json').write_text(json.dumps(model.model_json_schema(),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('Exported eleven schemas from current code; runtime validators also enforce cross-field invariants.')

if __name__=='__main__': main()
