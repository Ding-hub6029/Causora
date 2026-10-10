#!/usr/bin/env python3
"""Build and verify a complete Day5 source ZIP without credentials or caches.

This generates DELIVERY integrity hashes only. It never edits release approvals,
source-bound review hashes, model answers or historical scoring results.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IGNORE_DIRS = {"node_modules", ".next", ".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".runtime", ".mypy_cache", ".ruff_cache"}
IGNORE_SUFFIXES = (".pyc", ".pyo", ".tsbuildinfo")
SECRET_PATTERN = re.compile(rb"(?:sk-or-v1-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{20,}|rk-[A-Za-z0-9_-]{20,})")


def include(path):
    relative = path.relative_to(ROOT)
    if any(part in IGNORE_DIRS for part in relative.parts):
        return False
    if path.name.startswith(".env") and not path.name.endswith(".example"):
        return False
    if path.name.endswith(IGNORE_SUFFIXES):
        return False
    return True


def inventory():
    files = []
    for current, dirs, names in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in IGNORE_DIRS]
        for name in names:
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError("Symlinks are not accepted in a portable delivery: " + str(path))
            if include(path):
                files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if target.is_relative_to(ROOT):
        parser.error("Write ZIP outside the project to avoid self-inclusion.")
    target.parent.mkdir(parents=True, exist_ok=True)
    names = ("MANIFEST.sha256", "PACKAGE_FILE_LIST.csv")
    payloads = [p for p in inventory() if p.relative_to(ROOT).as_posix() not in names]
    suspects = []
    for p in payloads:
        data = p.read_bytes()
        if SECRET_PATTERN.search(data):
            # Never print or persist a matching value.
            suspects.append(p.relative_to(ROOT).as_posix())
    if suspects:
        raise ValueError("Credential-pattern review required in files: " + ", ".join(suspects))
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(["path", "bytes", "sha256"])
    for p in payloads:
        data = p.read_bytes()
        writer.writerow([p.relative_to(ROOT).as_posix(), len(data), sha(data)])
    # CSV deliberately excludes itself and MANIFEST. MANIFEST includes the CSV
    # and all payload files, but not itself, avoiding recursive checksums.
    (ROOT / "PACKAGE_FILE_LIST.csv").write_text(buf.getvalue(), encoding="utf-8", newline="")
    entries = [p for p in inventory() if p.name != "MANIFEST.sha256"]
    manifest = "".join(f"{sha(p.read_bytes())}  {p.relative_to(ROOT).as_posix()}\n" for p in entries)
    (ROOT / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    all_files = inventory()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for p in all_files:
            archive.write(p, "Causora/" + p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None, "ZIP CRC failure"
        expected = {"Causora/" + p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in all_files}
        assert set(archive.namelist()) == set(expected), "ZIP inventory differs"
        for name, digest in expected.items():
            assert sha(archive.read(name)) == digest, "ZIP byte mismatch: " + name
    result = {"status": "PASS", "zipPath": str(target), "zipSha256": sha(target.read_bytes()), "zipBytes": target.stat().st_size,
              "filesIncludingManifest": len(all_files), "manifestEntries": len(entries), "csvPayloadRows": len(payloads),
              "excluded": sorted(IGNORE_DIRS) + list(IGNORE_SUFFIXES) + ["non-example .env*"],
              "secretsPatternScan": "PASS", "zipCrc": "PASS", "zipByteMatch": "PASS",
              "note": "Native Windows execution not attested. Build artifacts are included; dependencies/caches are not."}
    receipt = target.with_suffix(".integrity.json")
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target.with_suffix(".sha256").write_text(result["zipSha256"] + "  " + target.name + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
