"""Command line for internal testing only; never an approval-ready API."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulation_day3.monte_carlo import run_unapproved_monte_carlo


def main() -> None:
    parser = argparse.ArgumentParser(description="Seeded 104-week synthetic MC preview; NOT a public success endpoint")
    parser.add_argument("preview", choices=["preview"])
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runs", type=int, choices=[1000, 10000], help="Explicit development/benchmark override")
    args = parser.parse_args()
    if "UNAPPROVED" not in args.out.name or args.out.exists():
        parser.error("output must be a new filename containing UNAPPROVED")
    request = json.loads(args.request.read_text(encoding="utf-8"))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    if args.runs is not None:
        policy["monteCarloRuns"] = args.runs
    preview = run_unapproved_monte_carlo(request, policy, project_root=args.project_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(preview, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{args.out}: {preview['monteCarloRuns']} real synthetic draws × 104 weeks × 9 cells; "
          "NOT APPROVED; no public API 200")


if __name__ == "__main__":
    main()
