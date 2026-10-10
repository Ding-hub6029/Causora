from pathlib import Path
import sys,json,time,hashlib,csv
BASE=Path(__file__).resolve().parents[2]
ROOT=(Path(__file__).parent/'Causora/backend/backend') if (Path(__file__).parent/'Causora').exists() else BASE/'work/github-day1-day4/Day5/Causora/backend/backend'
sys.path.insert(0,str(ROOT))
from simulation_day3.monte_carlo import run_unapproved_monte_carlo
OUT=Path(__file__).parent
request=json.loads((ROOT/'examples/simulate_request_v1.json').read_text(encoding='utf-8'))
policy=json.loads((ROOT/'simulation_day3/examples/UNAPPROVED_MC_POLICY.json').read_text(encoding='utf-8'))
policy['monteCarloRuns']=10000
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
results=[]
for seed in [1042026,1042026,1042027,1042028]:
    req=dict(request,seed=seed)
    started=time.perf_counter()
    preview=run_unapproved_monte_carlo(req,policy,project_root=ROOT)
    matrix=preview['computedMatrix']
    results.append({'seed':seed,'seconds':time.perf_counter()-started,'matrix':matrix,'matrixSha256':digest(matrix)})
assert results[0]['matrixSha256']==results[1]['matrixSha256']
max_delta=0.0
for row in results[2:]:
    for scenario,cells in row['matrix'].items():
        for idx,cell in enumerate(cells):
            reference=results[0]['matrix'][scenario][idx]
            max_delta=max(max_delta,abs(cell['stockoutProbability']-reference['stockoutProbability'])*100)
golden=json.loads((ROOT.parents[1]/'frontend/public/golden/verified_golden_e2e.json').read_text(encoding='utf-8'))
simulation=golden['simulationResponse']['data']['simulation']
rows=[]
for scenario,cells in simulation['matrix'].items():
    for cell in cells:
        assert sum(cell['breakdown'].values())==cell['expectedTco']
        rows.append({'scenario':scenario,'option':cell['optionId'],'expectedTcoUsd':cell['expectedTco'],
        'stockoutProbability':cell['stockoutProbability'],'serviceLevel':cell['serviceLevel'],'cashP90Usd':cell['cashOutflowP90'],**cell['breakdown']})
with (OUT/'final-numbers.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
report={'kind':'DAY6_MATH_REPLAY_AND_CAPTURED_GOLDEN_RECONCILIATION','sameSeedReproducible':True,
'crossSeedMaximumStockoutDifferencePercentagePoints':max_delta,'crossSeedWithin2pp':max_delta<=2,
'runsPerBenchmark':10000,'publicGoldenRuns':simulation['monteCarloRuns'],'goldenSimulationId':simulation['simulationId'],
'goldenNineCostTotalsReconciled':len(rows)==9,'benchmarkResults':results,
'limitations':['Engine previews are mathematical benchmarks, not new reviewed public runs.','Three selected seeds are a stability check, not a universal probability guarantee.','Golden snapshot has 1000 trials; do not claim the public site uses 10000 trials.','Cost sum check is separate from existing oracle/gated-service tests; it does not independently validate every distribution assumption.']}
(OUT/'numeric-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='benchmarkResults'}))
