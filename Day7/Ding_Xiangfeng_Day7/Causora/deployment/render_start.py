#!/usr/bin/env python3
"""Render production entry point for the reviewed Causora API.

This launcher intentionally delegates release-path setup to the existing reviewed
startup module.  It rejects both explicit development overrides before binding a
public socket.  It does not create any external deployment or contact a model.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend" / "backend"


def enforce_openrouter_mode(environ: dict[str, str] | None = None) -> None:
    """Force the approved transport and reject the legacy generic-provider path."""
    env = os.environ if environ is None else environ
    configured = env.get("CAUSORA_AI_PROVIDER", "").strip()
    if configured and configured.casefold() != "openrouter":
        raise ValueError("CAUSORA_AI_PROVIDER must be openrouter in production")
    # An inherited OPENAI_API_KEY/OPENAI_API_BASE must never select the legacy
    # generic provider when an operator omitted this non-secret selector.
    env["CAUSORA_AI_PROVIDER"] = "openrouter"
    env["CAUSORA_PUBLIC_REVIEW_ADMISSION"] = "YES"


def production_address(environ: dict[str, str] | None = None) -> tuple[str, int]:
    """Validate the hosting address and reject development-only environment flags."""
    env = os.environ if environ is None else environ
    prohibited = {
        "CAUSORA_DEV_UNREVIEWED_MODE": "The unreviewed development simulation override is prohibited in production.",
        "CAUSORA_DAY4_UNREVIEWED_PROVIDER_DEVELOPMENT_ONLY": "The unreviewed provider development override is prohibited in production.",
    }
    for key, message in prohibited.items():
        if env.get(key, "").strip():
            raise ValueError(f"{key}: {message}")
    host = env.get("HOST", "0.0.0.0").strip()
    if host != "0.0.0.0":
        raise ValueError("HOST must be 0.0.0.0 for a public Render web service")
    raw_port = env.get("PORT", "8000").strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be within 1..65535")
    return host, port


def configure_reviewed_release() -> None:
    if not BACKEND_ROOT.is_dir():
        raise RuntimeError(f"Backend directory is missing: {BACKEND_ROOT}")
    sys.path.insert(0, str(BACKEND_ROOT))
    from scripts.start_day4_reviewed import configure

    configure()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Validate production configuration without opening a socket.")
    args = parser.parse_args()
    try:
        host, port = production_address()
        enforce_openrouter_mode()
        configure_reviewed_release()
    except (RuntimeError, ValueError, SystemExit) as exc:
        message = str(exc) or "Reviewed release configuration is unavailable."
        print(f"Causora production startup refused: {message}", file=sys.stderr)
        raise SystemExit(2) from None
    if args.validate_only:
        print(f"Reviewed production configuration valid; would bind {host}:{port}.")
        return
    import uvicorn

    uvicorn.run("app.service:app", host=host, port=port, reload=False, proxy_headers=True)


if __name__ == "__main__":
    main()
