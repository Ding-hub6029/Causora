"""Runtime configuration for the local Causora Day 3 service."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION_V1 = "causora.contract.v1"
SCHEMA_VERSION_V2 = "causora.contract.v2"
TRACE_SCHEMA_VERSION = "causora.formula-trace.v1"
DEFAULT_DATASET_ID = "ds-001"
DEV_UNREVIEWED_MODE_LITERAL = "UNREVIEWED_DEV_ONLY"


def _path_from_env(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser().resolve() if value else None


def cors_origins() -> list[str]:
    """Read a comma-separated allowlist; local Next.js ports work by default."""
    raw = os.getenv("CAUSORA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def unreviewed_development_mode_enabled() -> bool:
    """Allow an explicitly named local-only integration mode, never a truthy shortcut.

    This mode exists so UI/API integration can exercise a real, seeded v2
    calculation before external human records are available. It is deliberately
    not enabled by values such as ``true`` or ``1`` and it never changes the
    default fail-closed reviewed route.
    """
    return os.getenv("CAUSORA_DEV_UNREVIEWED_MODE", "").strip() == DEV_UNREVIEWED_MODE_LITERAL


def review_bundle_path() -> Path | None:
    return _path_from_env("CAUSORA_REVIEW_BUNDLE_DIR")


def review_verifier_spec() -> str:
    """Built-in adapter validates Wang's supplied bundle; it cannot create one."""
    return os.getenv("CAUSORA_REVIEW_VERIFIER", "app.release_verifiers:verify_reviewed_bundle_record").strip()


def approved_policy_path() -> Path | None:
    return _path_from_env("CAUSORA_APPROVED_POLICY_PATH")


def policy_approval_record_path() -> Path | None:
    return _path_from_env("CAUSORA_POLICY_APPROVAL_RECORD_PATH")


def policy_verifier_spec() -> str:
    return os.getenv("CAUSORA_POLICY_VERIFIER", "app.release_verifiers:verify_team_policy_record").strip()


def trace_contract_v2_release_record_path() -> Path | None:
    return _path_from_env("CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD")


def trace_contract_v2_verifier_spec() -> str:
    return os.getenv("CAUSORA_TRACE_CONTRACT_V2_VERIFIER", "app.release_verifiers:verify_trace_contract_release").strip()


def common_api_contract_path() -> Path | None:
    return _path_from_env("CAUSORA_COMMON_API_CONTRACT_PATH")


def typescript_v2_types_path() -> Path | None:
    return _path_from_env("CAUSORA_TYPESCRIPT_V2_TYPES_PATH")


def frontend_v2_validator_path() -> Path | None:
    return _path_from_env("CAUSORA_FRONTEND_V2_VALIDATOR_PATH")


def trace_artifact_dir() -> Path:
    value = _path_from_env("CAUSORA_TRACE_ARTIFACT_DIR")
    destination = value if value is not None else PROJECT_ROOT / "artifacts" / "traces"
    destination.mkdir(parents=True, exist_ok=True)
    return destination
