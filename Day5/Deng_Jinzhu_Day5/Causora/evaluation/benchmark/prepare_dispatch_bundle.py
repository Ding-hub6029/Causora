#!/usr/bin/env python3
"""Write a model-facing Day 5 benchmark bundle without contacting a provider."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.benchmark.benchmark_common import PROMPT_PATHS, benchmark_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", required=True, choices=sorted(PROMPT_PATHS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    context = benchmark_context()
    prompt = PROMPT_PATHS[args.method].read_text(encoding="utf-8").rstrip()
    material = "\n\n".join([
        prompt,
        "## Frozen shared input supplied to the evaluated method",
        "Do not request or infer an answer key. Return results only for these cases.",
        "```json\n" + json.dumps(context["shared"], ensure_ascii=False, indent=2) + "\n```",
        "## Run identity supplied by the operator",
        json.dumps({
            "method": args.method,
            "commonInputSha256": context["sharedInputsSha256"],
            "promptSha256": context["promptSha256"][args.method],
            "expectedResultCaseIds": context["caseIds"],
        }, ensure_ascii=False, indent=2),
    ]) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(material, encoding="utf-8", newline="\n")
    print(json.dumps({"method": args.method, "output": str(args.output), "commonInputSha256": context["sharedInputsSha256"], "promptSha256": context["promptSha256"][args.method], "providerCallsMade": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
