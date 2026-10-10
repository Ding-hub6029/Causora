#!/usr/bin/env python3
"""Measure the unchanged Day 3 Monte Carlo engine at a fixed configuration.

This is a verification utility.  It invokes the internal unapproved preview API
so it cannot create a public success, approval, Golden Run, or Boardroom input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    # `resource` is a POSIX module and is intentionally absent on Windows.
    # Keep the timing benchmark usable there even when process RSS cannot be
    # collected by the standard library.
    import resource
except ModuleNotFoundError:  # pragma: no cover - exercised by a Windows host
    resource = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.portable_io import write_json_utf8_lf
from simulation_day3.monte_carlo import run_unapproved_monte_carlo


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _peak_rss_measurement() -> tuple[float | None, str, str | None]:
    """Return RSS when supported without making the benchmark platform-specific.

    Linux exposes `ru_maxrss` in KiB and macOS exposes it in bytes. Windows
    does not ship Python's POSIX `resource` module.  A missing or failed memory
    sample is therefore reported explicitly rather than failing an otherwise
    valid elapsed-time benchmark or inventing an RSS value.
    """
    if resource is None:
        return None, "unavailable", "resource module is unavailable on this platform"
    try:
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError, OSError, ValueError):
        return None, "unavailable", "resource.getrusage could not provide peak RSS"
    divisor = 1024 if sys.platform.startswith("linux") else 1024 * 1024
    return round(value / divisor, 3), "available", "resource.getrusage"


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the unchanged Causora Day 3 Monte Carlo engine.")
    parser.add_argument("--runs", type=int, choices=(1000, 10000), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    request = json.loads((ROOT / "examples" / "simulate_request_v1.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "simulation_day3" / "examples" / "UNAPPROVED_MC_POLICY.json").read_text(encoding="utf-8"))
    policy["monteCarloRuns"] = args.runs

    started_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started = time.perf_counter()
    result = run_unapproved_monte_carlo(request, policy, project_root=ROOT)
    elapsed = time.perf_counter() - started
    peak_rss_mib, peak_rss_status, peak_rss_source = _peak_rss_measurement()

    matrix = result["computedMatrix"]
    summary = {
        scenario: {
            cell["optionId"]: {
                "expectedTco": cell["expectedTco"],
                "stockoutProbability": cell["stockoutProbability"],
                "cashOutflowP90": cell["cashOutflowP90"],
            }
            for cell in cells
        }
        for scenario, cells in matrix.items()
    }
    report = {
        "kind": "CAUSORA_DAY4_MONTE_CARLO_PERFORMANCE_VERIFICATION_V1",
        "status": "UNREVIEWED_ENGINE_BENCHMARK_ONLY_NOT_A_PUBLIC_SIMULATION",
        "startedAtUtc": started_utc,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "cpuCount": os.cpu_count(),
        },
        "configuration": {
            "seed": request["seed"],
            "weeks": result["weeks"],
            "monteCarloRuns": args.runs,
            "requestSha256": _canonical_sha256(request),
            "policySha256": _canonical_sha256(policy),
            "engineSourceSha256": result["engineSourceSha256"],
            "engineInputPreviewId": result["previewId"],
        },
        "measurements": {
            "wallClockSeconds": round(elapsed, 6),
            "peakRssMiB": peak_rss_mib,
            "peakRssStatus": peak_rss_status,
            "peakRssSource": peak_rss_source,
        },
        "outputCheck": {
            "matrixSummary": summary,
            "matrixSummarySha256": _canonical_sha256(summary),
            "nineCellCount": sum(len(cells) for cells in matrix.values()),
            "traceWeekRecordCount": sum(len(trace["weeks"]) for traces in result["formulaTraces"].values() for trace in traces.values()),
            "formulaVersion": result["formulaVersion"],
            "noCalculationMeaningWasChanged": True,
        },
        "notes": [
            "N=1000 is the development-speed configuration; N=10000 is the PDF final-demo target.",
            "The same fixed request/seed is used for both runs, but the policy hash and preview ID differ because monteCarloRuns is intentionally part of the configuration identity.",
            "This benchmark uses only the unreviewed synthetic engine preview and cannot evidence human review, policy approval, contract release, Golden Run, or Boardroom readiness.",
            "On platforms without Python's resource module (including Windows), peakRssMiB is null and peakRssStatus is unavailable; wallClockSeconds remains valid.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json_utf8_lf(args.out, report, sort_keys=True)
    print(json.dumps({"runs": args.runs, "wallClockSeconds": report["measurements"]["wallClockSeconds"], "output": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
