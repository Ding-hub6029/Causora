"""Day 3 CLI: offline mock by default; explicit real integration only with both gates."""
from __future__ import annotations

import argparse
import asyncio
import importlib
from pathlib import Path
from typing import Callable

from .models import BoardroomSnapshot
from .orchestrator import run_parallel
from .provider import OfflineStubProvider, SandboxProxyProvider
from .wire_models import load_local_mock_snapshot, load_real_snapshot_input


def _load_verifier(spec: str) -> Callable[[BoardroomSnapshot], None]:
    module_name, marker, attribute = spec.partition(":")
    if not marker or not module_name or not attribute:
        raise ValueError("Verifier must use module:function syntax")
    callback = getattr(importlib.import_module(module_name), attribute, None)
    if not callable(callback):
        raise ValueError("Verifier reference is not callable")
    return callback


def _write_or_print(text: str, output: Path | None) -> None:
    if output is None:
        print(text)
        return
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing audit artifact")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(output)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Causora Wang Hao Day 3 independent role-draft runner")
    parser.add_argument("action", nargs="?", default="offline-mock",
                        choices=("offline-mock", "model-mock-smoke", "real-integration"))
    parser.add_argument("--scenario", choices=("baseline", "demand-drop", "lead-stress"), default="demand-drop")
    parser.add_argument("--output", type=Path, help="New JSON output only; existing files are never overwritten")
    parser.add_argument("--model", default="gpt-5-mini", help="Model proxy ID for opt-in model-mock-smoke only")
    parser.add_argument("--input-snapshot", type=Path, help="Strict hash-bound real SimulationResult integration JSON")
    parser.add_argument("--review-bundle", type=Path, help="Original verified Day2 bundle or current hash-bound human-receipt directory")
    parser.add_argument("--legacy-review-root", type=Path, help="Explicit combined Day2 source root for original bundle_manifest verification")
    parser.add_argument("--verifier", help="Required real gate, e.g. my_backend.jinzhu_verify:verify_simulation")
    args = parser.parse_args(argv)

    if args.action == "offline-mock":
        snapshot = load_local_mock_snapshot(args.scenario)
        provider = OfflineStubProvider()
        result = asyncio.run(run_parallel(snapshot, provider=provider))
        _write_or_print(result.model_dump_json(indent=2) + "\n", args.output)
        print("LOCAL_MOCK / OFFLINE_STUB only; no simulation, human approval, or decision readiness is claimed.")
        return

    if args.action == "model-mock-smoke":
        # This intentionally remains LOCAL_MOCK. Do not run it without an authorized
        # server-side proxy and a freshly checked model catalog.
        snapshot = load_local_mock_snapshot(args.scenario)
        provider = SandboxProxyProvider(args.model)
        result = asyncio.run(run_parallel(snapshot, provider=provider))
        _write_or_print(result.model_dump_json(indent=2) + "\n", args.output)
        print("LOCAL_MOCK / MODEL_PROXY only; output is not a live simulation or decision.")
        return

    if args.input_snapshot is None or args.review_bundle is None or not args.verifier:
        parser.error("real-integration requires --input-snapshot, --review-bundle, and --verifier")
    real_input = load_real_snapshot_input(args.input_snapshot)
    verifier = _load_verifier(args.verifier)
    result = asyncio.run(run_parallel(real_input.to_boardroom_snapshot(), provider=OfflineStubProvider(),
                                      review_bundle=args.review_bundle, simulation_verifier=verifier,
                                      legacy_review_root=args.legacy_review_root))
    _write_or_print(result.model_dump_json(indent=2) + "\n", args.output)
    print("SIMULATION_READY integration draft completed; decisionReady remains false and no Brief was generated.")


if __name__ == "__main__":
    main()
