#!/usr/bin/env python3
"""Start packaged Causora locally in simulation-only or historical replay mode.

No model credentials or dispatch authorization are inherited. No budget journal is
created, selected, reset or deleted. For separately authorized AI use the existing
reviewed backend launcher directly, not this convenience launcher.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SECRET_ENV = {
    "OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_BASE_URL", "OPENROUTER_API_KEY",
    "BUILT_IN_FORGE_API_KEY", "BUILT_IN_FORGE_API_URL",
}


def simulation_environment():
    env = dict(os.environ)
    for name in list(env):
        if name in SECRET_ENV or name.startswith("CAUSORA_OPENROUTER_"):
            env.pop(name, None)
    env.pop("CAUSORA_DEV_UNREVIEWED_MODE", None)
    env.pop("CAUSORA_DAY4_UNREVIEWED_PROVIDER_DEVELOPMENT_ONLY", None)
    env["CAUSORA_AI_PROVIDER"] = "openrouter"
    return env


def ensure_port_free(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Port {port} is occupied; no existing process was stopped.") from exc


def wait_ready(url, process, *, json_health=False, timeout=35):
    deadline = time.monotonic() + timeout
    # Never use inherited HTTP proxies for a loopback readiness check.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Child process exited ({process.returncode}); inspect its terminal output.")
        try:
            with opener.open(url, timeout=2) as response:
                body = response.read()
                if response.status == 200:
                    if not json_health or json.loads(body).get("data", {}).get("simulation") == "ready":
                        return
        except (OSError, ValueError):
            pass
        time.sleep(0.3)
    raise RuntimeError(f"Readiness timed out: {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("live", "static"), default="live")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=3000)
    args = parser.parse_args()
    if not all(1 <= p <= 65535 for p in (args.backend_port, args.frontend_port)) or args.backend_port == args.frontend_port:
        parser.error("Choose two different ports in 1..65535.")
    node = shutil.which("node")
    if not node:
        parser.error("Node.js 22+ is required.")
    build = ROOT / "frontend" / "builds" / args.mode / ".causora-build.json"
    if not build.is_file() or json.loads(build.read_text()).get("mode") != args.mode:
        parser.error("Build missing or mode mismatch: run npm ci and npm run build:previews in frontend first.")
    ensure_port_free(args.frontend_port)
    if args.mode == "live":
        ensure_port_free(args.backend_port)
    env = simulation_environment()
    children = []
    try:
        if args.mode == "live":
            backend = subprocess.Popen(
                [sys.executable, "scripts/start_day4_reviewed.py", "--port", str(args.backend_port)],
                cwd=ROOT / "backend/backend", env=env,
            )
            children.append(backend)
            wait_ready(f"http://127.0.0.1:{args.backend_port}/health", backend, json_health=True)
        env.update({"CAUSORA_FRONTEND_MODE": args.mode,
                    "CAUSORA_STATIC_ONLY": str(args.mode == "static").lower(),
                    "NEXT_PUBLIC_CAUSORA_STATIC_ONLY": str(args.mode == "static").lower(),
                    "CAUSORA_BACKEND_URL": f"http://127.0.0.1:{args.backend_port}",
                    "PORT": str(args.frontend_port), "HOST": "127.0.0.1"})
        frontend = subprocess.Popen([node, "scripts/serve-static.mjs"], cwd=ROOT / "frontend", env=env)
        children.append(frontend)
        wait_ready(f"http://127.0.0.1:{args.frontend_port}/", frontend)
        print(f"Causora {args.mode}: http://127.0.0.1:{args.frontend_port}/", flush=True)
        print("Simulation/replay only; live AI is disabled. Ctrl+C stops only these child processes.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        raise RuntimeError("A local service stopped unexpectedly.")
    except KeyboardInterrupt:
        print("Stopping local Causora processes.")
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)


if __name__ == "__main__":
    main()
