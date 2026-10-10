#!/usr/bin/env python3
"""Run local Day5 regression checks. This runner never dispatches a paid model.

Logs are written to an explicit fresh directory outside the immutable delivery
inventory by default. The existing benchmark/model captures are not overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--build", action="store_true", help="Rebuild static/live frontend and run production checks.")
    parser.add_argument("--local-http", action="store_true", help="Run no-key local HTTP simulation/evidence smoke checks.")
    args = parser.parse_args()
    if args.output:
        out = args.output.resolve()
        if out.exists() and any(out.iterdir()):
            parser.error("Output directory must be empty; never overwrite earlier logs.")
        out.mkdir(parents=True, exist_ok=True)
    else:
        out = Path(tempfile.mkdtemp(prefix="causora-day5-tests-"))
    env = dict(os.environ)
    for key in list(env):
        if key in {"OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_BASE_URL", "OPENROUTER_API_KEY", "BUILT_IN_FORGE_API_KEY", "BUILT_IN_FORGE_API_URL"} or key.startswith("CAUSORA_OPENROUTER_"):
            env.pop(key, None)
    env.pop("OPENROUTER_SCOPED_KEY_CONFIRMED", None)
    env.pop("CAUSORA_DEV_UNREVIEWED_MODE", None)
    env.pop("CAUSORA_DAY4_UNREVIEWED_PROVIDER_DEVELOPMENT_ONLY", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        parser.error("npm is required; install Node.js 22+ and run npm ci in frontend.")
    commands = [
        ("backend", ROOT / "backend/backend", [sys.executable, "-m", "pytest", "tests", "simulation_day1/tests", "simulation_day2/tests", "simulation_day3/tests", "-q", "-p", "no:cacheprovider"]),
        ("release-config", ROOT, [sys.executable, "deployment/render_start.py", "--validate-only"]),
        ("frontend", ROOT / "frontend", [npm, "test"]),
        ("frontend-typecheck", ROOT / "frontend", [npm, "run", "typecheck"]),
        ("frontend-lint", ROOT / "frontend", [npm, "run", "lint"]),
    ]
    agent_root = ROOT / "agents/wanghao-day3"
    for folder in ("tests_day5", "tests"):
        if (agent_root / folder).is_dir():
            commands.append(("ai-" + folder, agent_root, [sys.executable, "-m", "pytest", folder, "-q", "-p", "no:cacheprovider"]))
    eval_tests = ROOT / "evaluation/day5/tests"
    if eval_tests.is_dir():
        commands.append(("evaluation", ROOT, [sys.executable, "-m", "pytest", str(eval_tests), "-q", "-p", "no:cacheprovider"]))
    if args.build:
        commands.extend([
            ("frontend-build", ROOT / "frontend", [npm, "run", "build:previews"]),
            ("frontend-production", ROOT / "frontend", [npm, "run", "test:production"]),
        ])
    if args.local_http:
        commands.append(("local-http", ROOT, [sys.executable, "scripts/verify_day5_local.py", "--output", str(out / "local-http")]))
    results = []
    for name, cwd, command in commands:
        print("Running " + name, flush=True)
        with (out / (name + ".log")).open("w", encoding="utf-8") as log:
            current_env = dict(env)
            current_env["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(agent_root), str(ROOT / "backend/backend")))
            result = subprocess.run(command, cwd=cwd, env=current_env, stdout=log, stderr=subprocess.STDOUT)
        results.append({"name": name, "cwdRelative": cwd.relative_to(ROOT).as_posix(), "argv": command,
                        "exitCode": result.returncode, "log": name + ".log"})
    summary = {"kind": "OFFLINE_REGRESSION_NOT_MODEL_PERFORMANCE", "timeUtc": datetime.now(timezone.utc).isoformat(),
               "modelDispatchAuthorized": False, "commands": results,
               "status": "PASS" if all(row["exitCode"] == 0 for row in results) else "FAIL"}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['status']}: logs in {out}", flush=True)
    raise SystemExit(0 if summary["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
