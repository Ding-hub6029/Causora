"""CLI for explicit unapproved internal deterministic previews only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulation_day2.deterministic import ROOT, run_reviewed_internal, run_unreviewed_preview


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Jinzhu internal Day 2 deterministic engine; NOT a public /api/simulate server")
    parser.add_argument("action", choices=("preview", "reviewed-preview"))
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reviewed-bundle", type=Path)
    args = parser.parse_args(argv)
    if (args.action == "reviewed-preview") != (args.reviewed_bundle is not None):
        parser.error("reviewed-preview requires --reviewed-bundle; preview forbids it")
    if "UNAPPROVED" not in args.out.name:
        parser.error("internal preview filename must include UNAPPROVED")
    if args.out.exists():
        parser.error("refusing to overwrite existing preview")
    request = json.loads(args.request.read_text(encoding="utf-8"))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    if args.action == "reviewed-preview":
        result = run_reviewed_internal(request, policy, project_root=args.project_root.resolve(),
                                       reviewed_bundle=args.reviewed_bundle.resolve())
    else:
        result = run_unreviewed_preview(request, policy, project_root=args.project_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"{args.out}: 104 deterministic weeks × 9 cells; {result['reviewStatus']}; no MC/P90, public DTO or recommendation")


if __name__ == "__main__":
    main()
