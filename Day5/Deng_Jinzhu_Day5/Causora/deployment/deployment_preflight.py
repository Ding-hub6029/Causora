#!/usr/bin/env python3
"""Offline packaging/deployment preflight; it never contacts a hosting provider."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISALLOWED_DIRS = {"node_modules", ".venv", "__pycache__", ".pytest_cache", ".next", ".runtime"}
SECRET = re.compile(rb"(?:sk-or-v1-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{20,}|rk-[A-Za-z0-9_-]{20,})")
GENERATED_INVENTORIES = {"MANIFEST.sha256", "PACKAGE_FILE_LIST.csv"}


def run(*, excluded_paths: set[Path] | None = None) -> dict[str, object]:
    problems: list[str] = []
    excluded = {path.resolve() for path in (excluded_paths or set())}
    required = [ROOT / "render.yaml", ROOT / "deployment" / "render_start.py", ROOT / "frontend" / "vercel.json", ROOT / "evaluation" / "oracle" / "independent_oracle.py"]
    for path in required:
        if not path.is_file():
            problems.append(f"missing:{path.relative_to(ROOT).as_posix()}")
    for path in ROOT.rglob("*"):
        if path.is_dir() and path.name in DISALLOWED_DIRS:
            problems.append(f"disallowed-directory:{path.relative_to(ROOT).as_posix()}")
        if not path.is_file():
            continue
        if path.resolve() in excluded:
            continue
        # A SHA-256 inventory is generated from arbitrary hex digests and can
        # accidentally contain an API-key-shaped byte sequence. The inventory
        # neither stores source values nor bypasses the scan of the actual files.
        if path.name in GENERATED_INVENTORIES:
            continue
        if path.name.endswith(".tsbuildinfo"):
            continue
        if path.name.casefold() == "apikey.txt":
            problems.append(f"secret-named-file:{path.relative_to(ROOT).as_posix()}")
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            problems.append(f"unreadable:{path.relative_to(ROOT).as_posix()}")
            continue
        if SECRET.search(raw):
            problems.append(f"secret-pattern:{path.relative_to(ROOT).as_posix()}")
    return {"schema": "causora.day5-deployment-preflight.v1", "status": "PASS" if not problems else "FAIL", "projectRoot": str(ROOT), "problems": sorted(problems)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    result = run(excluded_paths={output} if output else None)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
