#!/usr/bin/env python3
"""Start the explicit UNREVIEWED / DEVELOPMENT ONLY Causora Day 3 API.

This script is the only supported convenience entry point for pre-review
frontend/API integration. It clears review/policy/release configuration so a
run cannot be mistaken for a reviewed one, then sets the exact mode literal.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.config import DEV_UNREVIEWED_MODE_LITERAL  # noqa: E402


REVIEW_ENVIRONMENT_VARIABLES = (
    "CAUSORA_REVIEW_BUNDLE_DIR", "CAUSORA_REVIEW_VERIFIER",
    "CAUSORA_APPROVED_POLICY_PATH", "CAUSORA_POLICY_APPROVAL_RECORD_PATH", "CAUSORA_POLICY_VERIFIER",
    "CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD", "CAUSORA_COMMON_API_CONTRACT_PATH",
    "CAUSORA_TYPESCRIPT_V2_TYPES_PATH", "CAUSORA_FRONTEND_V2_VALIDATOR_PATH",
    "CAUSORA_TRACE_CONTRACT_V2_VERIFIER",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    for key in REVIEW_ENVIRONMENT_VARIABLES:
        os.environ.pop(key, None)
    os.environ["CAUSORA_DEV_UNREVIEWED_MODE"] = DEV_UNREVIEWED_MODE_LITERAL
    os.environ.setdefault("CAUSORA_TRACE_ARTIFACT_DIR", str(ROOT / "artifacts" / "traces" / "unreviewed-development"))
    print("=" * 76)
    print("UNREVIEWED — DEVELOPMENT ONLY")
    print("No Wang review, policy approval, or v2 release record is loaded.")
    print("Responses are v2-shaped for integration testing but are NOT decision-ready.")
    print(f"API: http://{args.host}:{args.port}   Dataset: ds-001")
    print("=" * 76)
    import uvicorn
    uvicorn.run("app.service:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
