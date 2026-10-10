#!/usr/bin/env python3
"""Validate and independently score one redacted external benchmark capture."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.benchmark.benchmark_common import benchmark_context
from evaluation.benchmark.score_shared_benchmark import score_completed_capture, validate_capture


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", required=True, choices=["plain_llm", "llm_plus_code"])
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.capture.read_text(encoding="utf-8"))
    capture = validate_capture(payload, args.method, benchmark_context())
    result = {
        "schema": "causora.day5-benchmark-capture-validation.v1",
        "method": args.method,
        "captureStatus": capture["status"],
        "captureValidationStatus": "VALID",
        "scoring": score_completed_capture(capture, benchmark_context()) if capture["status"] == "COMPLETED" else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"captureStatus": result["captureStatus"], "scoringStatus": (result["scoring"] or {}).get("scoringStatus", "NOT_SCORED"), "providerCallsMade": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
