"""Fail-closed HTTP adapter for the Day 4 Boardroom workflow.

This module deliberately owns the transport boundary only.  It never runs the
Monte Carlo engine, never turns development output into reviewed output, and
imports the independently-owned ``agent_day4`` package only when a formal
Boardroom request is made.  Successful simulation responses are registered by
``app.service`` in a small, immutable, process-local repository so a
Boardroom request is bound to the exact current simulation that produced it.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import json
import logging
import os
import re
import subprocess
import sys
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4

from fastapi import APIRouter, Body, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import PROJECT_ROOT, SCHEMA_VERSION_V1
from app.contracts_v2 import ApiSuccessV2, REVIEWED_EXECUTION_MODE
from simulation_day1.interfaces import validate_reviewed_contract
from simulation_day1.wire_models import BoardroomRequest, BoardroomSuccess, EvidenceSuccess


PUBLIC_EVIDENCE_IDS = ("EV-014", "EV-019", "EV-021", "EV-024", "EV-027")
OPTIONAL_EVIDENCE_IDS = ("EV-020",)
ALLOWED_EVIDENCE_IDS = frozenset(PUBLIC_EVIDENCE_IDS + OPTIONAL_EVIDENCE_IDS)
_REQUEST_ID_LIMIT = 128
_DEFAULT_REPOSITORY_LIMIT = 16
_SAFE_REASON = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


class BoardroomAdapterError(ValueError):
    """A sanitized adapter error suitable for a v1 API failure envelope."""

    def __init__(self, reason: str, message: str, *, status: int = 503,
                 code: str = "simulation_failed", headers: Mapping[str, str] | None = None):
        super().__init__(message)
        self.reason = reason if _SAFE_REASON.fullmatch(reason) else "boardroom_adapter_failed"
        self.message = message
        self.status = status
        self.code = code
        self.headers = dict(headers or {})


class RegistrationError(BoardroomAdapterError):
    """A simulation was not safe to retain as a Boardroom input."""

    def __init__(self, reason: str, message: str):
        super().__init__(reason, message, status=503, code="simulation_failed")


def _detach(value: Any) -> Any:
    """Deep-copy JSON data while rejecting non-wire values such as NaN."""
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise RegistrationError("simulation_record_invalid", "Simulation output cannot be retained safely.") from exc


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return copy.deepcopy(value)


def _repository_limit() -> int:
    raw = os.getenv("CAUSORA_BOARDROOM_REPOSITORY_LIMIT", str(_DEFAULT_REPOSITORY_LIMIT)).strip()
    try:
        limit = int(raw)
    except ValueError:
        return _DEFAULT_REPOSITORY_LIMIT
    return limit if 1 <= limit <= 128 else _DEFAULT_REPOSITORY_LIMIT


def _safe_header_value(value: str) -> str:
    return value if value and "\r" not in value and "\n" not in value else "unavailable"


def _canonical_request_id(request: Request) -> str:
    """Return an exact valid outbound correlation ID, never a silently trimmed one."""
    supplied = request.headers.get("X-Request-Id")
    if supplied is None:
        return f"req-{uuid4().hex}"
    if not supplied or len(supplied) > _REQUEST_ID_LIMIT or "\r" in supplied or "\n" in supplied:
        raise BoardroomAdapterError(
            "invalid_request_id", "X-Request-Id must be a non-empty single-line value of at most 128 characters.",
            status=422, code="validation_error",
        )
    # Keep the caller's bytes-as-decoded-by-ASGI exactly.  In particular, do
    # not use strip() here: the frontend verifies an exact echo.
    return supplied


def _headers(request_id: str, *, current_simulation_id: str | None = None,
             provider_mode: str | None = None, critic_status: str | None = None) -> dict[str, str]:
    result = {"Cache-Control": "no-store", "X-Request-Id": request_id}
    if current_simulation_id:
        result["X-Causora-Current-Simulation"] = _safe_header_value(current_simulation_id)
    if provider_mode:
        result["X-Causora-Provider-Mode"] = provider_mode
    if critic_status:
        result["X-Causora-Critic-Status"] = critic_status
    return result


def _failure(error: BoardroomAdapterError, request_id: str, *,
             current_simulation_id: str | None = None) -> JSONResponse:
    headers = _headers(
        request_id,
        current_simulation_id=current_simulation_id,
        provider_mode=error.headers.get("X-Causora-Provider-Mode"),
        critic_status=error.headers.get("X-Causora-Critic-Status"),
    )
    body = {
        "schemaVersion": SCHEMA_VERSION_V1,
        "requestId": request_id,
        "error": {
            "code": error.code,
            "message": error.message,
            "details": {"reason": error.reason},
            "requestId": request_id,
        },
    }
    return JSONResponse(status_code=error.status, content=body, headers=headers)


# The first five IDs are publicly returned by the pre-existing source registry.
# EV-020 is accepted if its reviewed source registry explicitly supplies it; the
# adapter never invents an evidence identifier to make a record look reviewed.
_EVIDENCE_CONTRACT_FIELDS: dict[str, tuple[str, str]] = {
    "EV-014": ("renewalNoticeDays", "days"),
    "EV-019": ("renewalTermMonths", "months"),
    "EV-021": ("renewalPriceIncreasePct", "percent"),
    "EV-024": ("minPurchaseShareA", "percent"),
    "EV-027": ("terminationFeeUsd", "money"),
}
_EVIDENCE_UNITS = {"EV-014": "days", "EV-019": "months", "EV-021": "percent", "EV-024": "share", "EV-027": "USD"}
_EV020_QUOTE = "The agreement automatically renews for 24 months at a 14% higher unit price."
_SOURCE_TEXT_CACHE: dict[tuple[Path, str, int], str] = {}
_SOURCE_TEXT_LOCK = threading.Lock()


def _resolve_source(source_root: Path, source_file: str) -> Path:
    if not isinstance(source_file, str) or not source_file or "\x00" in source_file:
        raise RegistrationError("evidence_source_invalid", "Evidence source is unavailable.")
    relative = Path(source_file)
    if relative.is_absolute() or ".." in relative.parts:
        raise RegistrationError("evidence_source_invalid", "Evidence source is unavailable.")
    candidates = (source_root / relative, source_root / "public" / "demo" / relative)
    root = source_root.resolve()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_relative_to(root) and resolved.is_file():
            return resolved
    raise RegistrationError("evidence_source_invalid", "Evidence source is unavailable.")


def _source_text(path: Path, *, page: int) -> str:
    try:
        source_bytes = path.read_bytes()
    except OSError as exc:
        raise RegistrationError("evidence_source_invalid", "Evidence source is unavailable.") from exc
    digest = hashlib.sha256(source_bytes).hexdigest()
    cache_key = (path.resolve(), digest, page)
    with _SOURCE_TEXT_LOCK:
        cached = _SOURCE_TEXT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        if path.suffix.lower() == ".pdf":
            import pymupdf
            with pymupdf.open(path) as document:
                if not 1 <= page <= document.page_count:
                    raise ValueError("Evidence page outside source document")
                text = document[page - 1].get_text()
        else:
            text = source_bytes.decode("utf-8", errors="replace")
    except (OSError, ValueError, ImportError) as exc:
        raise RegistrationError("evidence_source_unreadable", "Evidence source cannot be verified.") from exc
    with _SOURCE_TEXT_LOCK:
        _SOURCE_TEXT_CACHE[cache_key] = text
    return text


def _numeric_value(value: Any, kind: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RegistrationError("evidence_value_invalid", "Evidence value does not match the simulation contract.")
    if kind in {"days", "months", "money"}:
        return int(value)
    return float(value)


def _value_matches_contract(extracted: str, contract_value: Any, kind: str) -> bool:
    compact = extracted.strip().replace(",", "")
    if kind == "days":
        found = re.fullmatch(r"(\d+)\s+days?", compact, flags=re.IGNORECASE)
        return bool(found and int(found.group(1)) == _numeric_value(contract_value, kind))
    if kind == "months":
        found = re.fullmatch(r"(\d+)\s+months?", compact, flags=re.IGNORECASE)
        return bool(found and int(found.group(1)) == _numeric_value(contract_value, kind))
    if kind == "percent":
        found = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)%", compact)
        return bool(found and abs(float(found.group(1)) / 100 - float(_numeric_value(contract_value, kind))) < 1e-12)
    if kind == "money":
        found = re.fullmatch(r"\$?\s*(\d+(?:\.0+)?)", compact)
        return bool(found and int(float(found.group(1))) == _numeric_value(contract_value, kind))
    return False


def verify_evidence_registry(contract: Mapping[str, Any], evidence: Iterable[Mapping[str, Any]],
                             source_root: Path) -> tuple[dict[str, Any], ...]:
    """Recompute public evidence truth from its source, quote, and contract value.

    The legacy ``quoteMatched`` / score flags are inputs only; this verifier
    sets them from fresh source text rather than trusting a caller supplied
    success flag.  No unknown IDs are permitted and all five public IDs must
    remain available for the Boardroom pipeline.
    """
    if not isinstance(contract, Mapping):
        raise RegistrationError("simulation_record_invalid", "Simulation contract is unavailable.")
    values = list(evidence)
    by_id: dict[str, Mapping[str, Any]] = {}
    for item in values:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            raise RegistrationError("evidence_registry_invalid", "Evidence registry is invalid.")
        evidence_id = item["id"]
        if evidence_id not in ALLOWED_EVIDENCE_IDS or evidence_id in by_id:
            raise RegistrationError("evidence_registry_invalid", "Evidence registry contains an unsupported identifier.")
        by_id[evidence_id] = item
    if set(PUBLIC_EVIDENCE_IDS) - set(by_id):
        raise RegistrationError("evidence_registry_incomplete", "The current simulation lacks required public evidence.")
    declared_ids = contract.get("evidenceIds")
    if not isinstance(declared_ids, list) or set(declared_ids) != set(PUBLIC_EVIDENCE_IDS):
        raise RegistrationError("evidence_registry_invalid", "Simulation contract evidence identifiers are incomplete.")
    # Existing public v1 registry records retain five IDs.  EV-020 is already a
    # reviewed trace/provenance ID, not an invented identifier; materialize its
    # original clause record when a reviewed trace requires it.
    if "EV-020" not in by_id:
        renewal = by_id["EV-019"]
        by_id["EV-020"] = {
            "id": "EV-020", "sourceFile": renewal.get("sourceFile"), "page": renewal.get("page"),
            "quote": _EV020_QUOTE, "locatorBbox": None, "extractedField": "auto_renew",
            "extractedValue": True, "unit": "boolean",
        }

    verified: list[dict[str, Any]] = []
    for evidence_id in (*PUBLIC_EVIDENCE_IDS, *OPTIONAL_EVIDENCE_IDS):
        item = by_id[evidence_id]
        source_file, quote, extracted = item.get("sourceFile"), item.get("quote"), item.get("extractedValue")
        page = item.get("page")
        if (not isinstance(source_file, str) or not isinstance(quote, str) or not quote or
                isinstance(page, bool) or not isinstance(page, int) or page < 1):
            raise RegistrationError("evidence_registry_invalid", "Evidence registry is invalid.")
        path = _resolve_source(source_root, source_file)
        source_text = _source_text(path, page=page)
        if quote not in source_text:
            raise RegistrationError("evidence_source_mismatch", "Evidence quote or extracted value no longer matches its source.")
        if evidence_id in _EVIDENCE_CONTRACT_FIELDS:
            field, kind = _EVIDENCE_CONTRACT_FIELDS[evidence_id]
            if not isinstance(extracted, str) or not extracted or extracted not in quote or extracted not in source_text or field not in contract or not _value_matches_contract(extracted, contract[field], kind):
                raise RegistrationError("evidence_value_invalid", "Evidence value does not match the simulation contract.")
        else:
            # EV-020 is a conditional clause, never an assertion that a legal
            # result is unconditional.  The dated contract calculation remains
            # the source of renewalLocked.
            if quote != _EV020_QUOTE or item.get("extractedField") != "auto_renew" or extracted is not True:
                raise RegistrationError("evidence_value_invalid", "Conditional renewal evidence is invalid.")
        normalized = _detach(dict(item))
        # Preserve the frozen public EvidenceRecord DTO.  Source hashes and
        # typed extraction units are private verifier inputs added only by the
        # parent-owned enrich_evidence helper at formal-pipeline handoff.
        normalized.pop("sourceSha256", None)
        normalized.pop("source_sha256", None)
        normalized.pop("unit", None)
        normalized["matchMethod"] = "exact"
        normalized["matchScore"] = 1.0
        normalized["quoteMatched"] = True
        verified.append(normalized)
    return tuple(verified)


SourceVerificationCallback = Callable[[Mapping[str, Any], tuple[dict[str, Any], ...], Path], None]


@dataclass(frozen=True)
class RegisteredSimulation:
    """Internal immutable snapshot of one successful simulation response."""

    dataset_id: str
    simulation_id: str
    data_version: str
    simulation_request_id: str
    execution_mode: str
    decision_ready: bool
    simulation_request: Mapping[str, Any]
    success: Mapping[str, Any]
    contract: Mapping[str, Any]
    evidence: tuple[Mapping[str, Any], ...]
    source_root: Path
    sequence: int

    @property
    def key(self) -> tuple[str, str]:
        return (self.simulation_id, self.data_version)

    def verified_run_arguments(self) -> dict[str, Any]:
        """Return fresh mutable JSON values for the independently-owned input verifier."""
        evidence = tuple(_thaw(item) for item in self.evidence)
        _ensure_agent_package_on_path()
        try:
            evidence_module = importlib.import_module("agent_day4.evidence")
            enrich = getattr(evidence_module, "enrich_evidence")
            evidence = tuple(enrich(evidence, source_root=self.source_root, contract=_thaw(self.contract)))
        except (ImportError, AttributeError) as exc:
            raise BoardroomAdapterError("boardroom_pipeline_unavailable", "Boardroom review is not configured.",
                                        status=503, code="simulation_failed") from exc
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise BoardroomAdapterError("simulation_source_unverified", "Current simulation inputs cannot be verified.",
                                        status=503, code="simulation_failed") from exc
        return {
            "simulation_request": _thaw(self.simulation_request),
            "simulation_response": _thaw(self.success),
            "contract": _thaw(self.contract),
            "evidence": evidence,
            "source_root": self.source_root,
            "simulation_request_id": self.simulation_request_id,
        }

    def evidence_record(self, evidence_id: str) -> dict[str, Any] | None:
        for item in self.evidence:
            if item.get("id") == evidence_id:
                public = _thaw(item)
                # The internal conditional-clause assertion is boolean; the
                # public value must also literally occur in its source quote.
                # This is a clause-presence phrase, not a legal-state assertion.
                if isinstance(public.get("extractedValue"), bool):
                    public["extractedValue"] = "automatically renews"
                # PyMuPDF search coordinates use a top-left origin, whereas the
                # Ding PDF.js locator consumes bottom-left PDF user-space points
                # and applies viewport rotation/scale itself. Never pass a raw
                # PyMuPDF rectangle through as if both coordinate systems match.
                from app.evidence_locator import EvidenceLocatorError, pdfjs_user_space_bbox
                try:
                    source = _resolve_source(self.source_root, str(public.get("sourceFile", "")))
                    # The strict v1 Pydantic DTO expects a fixed tuple. JSON
                    # serialization still emits this as the public four-number
                    # array required by Ding's TypeScript client.
                    public["locatorBbox"] = tuple(pdfjs_user_space_bbox(
                        source, int(public["page"]), str(public["quote"])
                    ))
                except (EvidenceLocatorError, KeyError, TypeError, ValueError) as exc:
                    raise BoardroomAdapterError(
                        "evidence_locator_unavailable", "Evidence source coordinates cannot be verified.",
                        status=503, code="simulation_failed",
                    ) from exc
                return public
        return None


class SimulationRepository:
    """Bounded process-local current-run registry with explicit stale detection."""

    def __init__(self, *, max_records: int | None = None,
                 source_verifiers: Iterable[SourceVerificationCallback] = ()) -> None:
        self._max_records = max_records if max_records is not None else _repository_limit()
        if not isinstance(self._max_records, int) or self._max_records < 1:
            raise ValueError("max_records must be a positive integer")
        self._source_verifiers = tuple(source_verifiers)
        self._records: OrderedDict[tuple[str, str], RegisteredSimulation] = OrderedDict()
        self._latest_by_dataset: dict[str, tuple[str, str]] = {}
        self._latest_global: tuple[str, str] | None = None
        self._sequence = 0
        self._lock = threading.RLock()

    def register(self, request_dict: Mapping[str, Any], success: Mapping[str, Any], contract: Mapping[str, Any],
                 evidence: Iterable[Mapping[str, Any]], source_root: Path | str,
                 simulation_request_id: str) -> RegisteredSimulation:
        request = _detach(request_dict)
        response = _detach(success)
        contract_copy = _detach(contract)
        if not isinstance(request, dict) or not isinstance(response, dict) or not isinstance(contract_copy, dict):
            raise RegistrationError("simulation_record_invalid", "Simulation record is invalid.")
        if not isinstance(simulation_request_id, str) or not simulation_request_id:
            raise RegistrationError("simulation_record_invalid", "Simulation request identity is unavailable.")
        try:
            source = Path(source_root).resolve()
        except (TypeError, OSError) as exc:
            raise RegistrationError("evidence_source_invalid", "Evidence source is unavailable.") from exc
        if not source.is_dir():
            raise RegistrationError("evidence_source_invalid", "Evidence source is unavailable.")
        try:
            parsed = ApiSuccessV2.model_validate(response).model_dump(mode="json")
            validate_reviewed_contract(contract_copy)
        except (ValidationError, ValueError, TypeError) as exc:
            raise RegistrationError("simulation_record_invalid", "Simulation output or contract is invalid.") from exc
        dataset_id = request.get("datasetId")
        if not isinstance(dataset_id, str) or not dataset_id:
            raise RegistrationError("simulation_record_invalid", "Simulation request dataset identity is unavailable.")
        if parsed["requestId"] != simulation_request_id:
            raise RegistrationError("simulation_record_invalid", "Simulation request identity does not match its response.")
        simulation = parsed["data"]["simulation"]
        if parsed["dataVersion"] != simulation["dataVersion"]:
            raise RegistrationError("simulation_record_invalid", "Simulation data version is inconsistent.")
        context = parsed["data"]["executionContext"]
        verified_evidence = verify_evidence_registry(contract_copy, evidence, source)
        for verifier in self._source_verifiers:
            try:
                verifier(contract_copy, verified_evidence, source)
            except BoardroomAdapterError:
                raise
            except Exception as exc:
                raise RegistrationError("evidence_source_unverified", "Evidence source cannot be verified.") from exc
        record = RegisteredSimulation(
            dataset_id=dataset_id,
            simulation_id=simulation["simulationId"],
            data_version=simulation["dataVersion"],
            simulation_request_id=simulation_request_id,
            execution_mode=context["mode"],
            decision_ready=context["decisionReady"],
            simulation_request=_freeze(request),
            success=_freeze(parsed),
            contract=_freeze(contract_copy),
            evidence=tuple(_freeze(item) for item in verified_evidence),
            source_root=source,
            sequence=0,
        )
        with self._lock:
            self._sequence += 1
            record = RegisteredSimulation(**{**record.__dict__, "sequence": self._sequence})
            key = record.key
            # Re-registering an identical deterministic simulation refreshes its
            # request identity without retaining aliases to a previous response.
            self._records.pop(key, None)
            self._records[key] = record
            self._latest_by_dataset[record.dataset_id] = key
            self._latest_global = key
            while len(self._records) > self._max_records:
                retired_key, retired = self._records.popitem(last=False)
                if self._latest_by_dataset.get(retired.dataset_id) == retired_key:
                    alternatives = [candidate for candidate in self._records.values() if candidate.dataset_id == retired.dataset_id]
                    if alternatives:
                        self._latest_by_dataset[retired.dataset_id] = alternatives[-1].key
                    else:
                        self._latest_by_dataset.pop(retired.dataset_id, None)
                if self._latest_global == retired_key:
                    self._latest_global = next(reversed(self._records), None) if self._records else None
        return record

    def _verify_current_sources(self, record: RegisteredSimulation) -> None:
        verified = verify_evidence_registry(_thaw(record.contract), (_thaw(item) for item in record.evidence), record.source_root)
        for verifier in self._source_verifiers:
            try:
                verifier(_thaw(record.contract), verified, record.source_root)
            except BoardroomAdapterError:
                raise
            except Exception as exc:
                raise RegistrationError("evidence_source_unverified", "Evidence source cannot be verified.") from exc

    def resolve_formal(self, request: BoardroomRequest) -> RegisteredSimulation:
        key = (request.simulationId, request.dataVersion)
        with self._lock:
            record = self._records.get(key)
            if record is None:
                known_simulation = any(candidate.simulation_id == request.simulationId for candidate in self._records.values())
                reason = "stale_simulation" if known_simulation else "simulation_not_found"
                raise BoardroomAdapterError(reason, "Boardroom request does not resolve to a retained current simulation.",
                                            status=422, code="validation_error")
            latest_key = self._latest_by_dataset.get(record.dataset_id)
            if latest_key != key:
                latest = self._records.get(latest_key) if latest_key else None
                headers = {"X-Causora-Current-Simulation": latest.simulation_id} if latest else {}
                raise BoardroomAdapterError("stale_simulation", "Boardroom request refers to a stale simulation run.",
                                            status=422, code="validation_error", headers=headers)
        # Source bytes are re-read outside the repository lock.  A changed PDF
        # invalidates a request rather than silently retaining old truth flags.
        self._verify_current_sources(record)
        if record.execution_mode != REVIEWED_EXECUTION_MODE or not record.decision_ready:
            raise BoardroomAdapterError("review_pending", "A formal Boardroom review requires a reviewed, decision-ready simulation.",
                                        status=503, code="simulation_failed")
        return record

    def current(self) -> RegisteredSimulation:
        with self._lock:
            if self._latest_global is None or self._latest_global not in self._records:
                raise BoardroomAdapterError("simulation_not_found", "No current simulation is available.", status=404, code="not_found")
            record = self._records[self._latest_global]
        self._verify_current_sources(record)
        return record

    def clear(self) -> None:
        """Test/support helper; no public HTTP endpoint exposes this operation."""
        with self._lock:
            self._records.clear()
            self._latest_by_dataset.clear()
            self._latest_global = None


repository = SimulationRepository()


def register_simulation(request_dict: Mapping[str, Any], success: Mapping[str, Any], contract: Mapping[str, Any],
                        evidence: Iterable[Mapping[str, Any]], source_root: Path | str,
                        simulation_request_id: str) -> RegisteredSimulation:
    """Register exactly one already-computed v2 simulation; never recompute it.

    This is intentionally importable by service wiring and tests.  It validates
    the response identity/dataVersion and source-backed evidence before making
    the new run the current run for that dataset.
    """
    return repository.register(request_dict, success, contract, evidence, source_root, simulation_request_id)


def _ensure_agent_package_on_path() -> None:
    agent_root = PROJECT_ROOT.parent.parent / "agents" / "wanghao-day3"
    if agent_root.is_dir() and str(agent_root) not in sys.path:
        sys.path.insert(0, str(agent_root))


def _agent_modules() -> tuple[Any, Any, Any]:
    """Lazy imports keep existing Day 3 tests runnable before Day 4 is installed."""
    _ensure_agent_package_on_path()
    try:
        return (
            importlib.import_module("agent_day4.inputs"),
            importlib.import_module("agent_day4.pipeline"),
            importlib.import_module("agent_day4.wire"),
        )
    except (ImportError, AttributeError) as exc:
        raise BoardroomAdapterError("boardroom_pipeline_unavailable", "Boardroom review is not configured.",
                                    status=503, code="simulation_failed") from exc


def _looks_like_fixture(provider: Any) -> bool:
    values = [provider.__class__.__name__, str(getattr(provider, "kind", "")), str(getattr(provider, "mode", ""))]
    if bool(getattr(provider, "TEST_FIXTURE_ONLY", False)):
        return True
    return any("fixture" in value.lower() or "test_only" in value.lower() for value in values)


def _normalise_runtime(runtime: Any, pipeline_config_type: type[Any]) -> tuple[Any, Any, Any, Any]:
    if isinstance(runtime, Mapping):
        provider = runtime.get("provider")
        critic_provider = runtime.get("critic_provider", runtime.get("criticProvider"))
        fallback_provider = runtime.get("fallback_provider", runtime.get("fallbackProvider"))
        config = runtime.get("config", runtime.get("pipeline_config"))
    elif isinstance(runtime, tuple) and len(runtime) == 4:
        provider, critic_provider, fallback_provider, config = runtime
    else:
        provider = getattr(runtime, "provider", None)
        critic_provider = getattr(runtime, "critic_provider", getattr(runtime, "criticProvider", None))
        fallback_provider = getattr(runtime, "fallback_provider", getattr(runtime, "fallbackProvider", None))
        config = getattr(runtime, "config", getattr(runtime, "pipeline_config", None))
    if provider is None or critic_provider is None:
        raise BoardroomAdapterError("provider_unavailable", "Boardroom provider configuration is unavailable.",
                                    status=503, code="simulation_failed")
    if any(_looks_like_fixture(item) for item in (provider, critic_provider, fallback_provider) if item is not None):
        raise BoardroomAdapterError("provider_configuration_invalid", "Test fixture providers are not allowed for formal Boardroom review.",
                                    status=503, code="simulation_failed")
    if config is None:
        config = pipeline_config_type()
    return provider, critic_provider, fallback_provider, config


def _load_formal_runtime(pipeline_config_type: type[Any]) -> tuple[Any, Any, Any, Any]:
    """Construct real providers lazily, only after a formal record is resolved.

    Parent-owned provider/wire code should export ``load_formal_runtime`` (or
    ``load_formal_runtime_from_env``) and return provider, critic provider,
    same-family fallback provider, and PipelineConfig.  A few equivalent names
    are accepted to keep this boundary backwards-compatible while Day 4 is
    being integrated; no fixture provider is ever accepted here.
    """
    _ensure_agent_package_on_path()
    try:
        provider_module = importlib.import_module("agent_day4.provider")
        wire_module = importlib.import_module("agent_day4.wire")
    except ImportError as exc:
        raise BoardroomAdapterError("provider_unavailable", "Boardroom provider configuration is unavailable.",
                                    status=503, code="simulation_failed") from exc
    factories: list[Callable[[], Any]] = []
    for module in (provider_module, wire_module):
        for name in ("load_formal_runtime", "load_formal_runtime_from_env", "formal_runtime_from_env",
                     "providers_from_env", "load_providers_from_env"):
            candidate = getattr(module, name, None)
            if callable(candidate):
                factories.append(candidate)
    if not factories:
        raise BoardroomAdapterError("provider_unavailable", "Boardroom provider configuration is unavailable.",
                                    status=503, code="simulation_failed")
    last_error: Exception | None = None
    for factory in factories:
        try:
            return _normalise_runtime(factory(), pipeline_config_type)
        except BoardroomAdapterError:
            raise
        except Exception as exc:
            # Provider construction may raise its own RuntimeError subclass
            # (for example a missing dedicated key). Keep that failure inside
            # the public v1 error envelope rather than emitting an HTML 500.
            # Cancellation is not caught: this factory is synchronous and
            # asyncio.CancelledError is a BaseException.
            last_error = exc
    raise BoardroomAdapterError("provider_unavailable", "Boardroom provider configuration is unavailable.",
                                status=503, code="simulation_failed") from last_error


def _make_verified_run(record: RegisteredSimulation, inputs_module: Any) -> Any:
    verified_run_type = getattr(inputs_module, "VerifiedRun", None)
    validate_run = getattr(inputs_module, "validate_run", None)
    if not callable(verified_run_type) or not callable(validate_run):
        raise BoardroomAdapterError("boardroom_pipeline_unavailable", "Boardroom review is not configured.",
                                    status=503, code="simulation_failed")
    try:
        run = verified_run_type(**record.verified_run_arguments())
        # Public transport is always formal.  require_reviewed=False is reserved
        # for the parent-owned internal CLI and is intentionally never used here.
        return validate_run(run, require_reviewed=True)
    except BoardroomAdapterError:
        raise
    except (OSError, ValueError, TypeError, KeyError, ValidationError) as exc:
        raise BoardroomAdapterError("simulation_source_unverified", "Current simulation inputs cannot be verified.",
                                    status=503, code="simulation_failed") from exc


def _pipeline_error(exc: Exception) -> BoardroomAdapterError:
    if isinstance(exc, BoardroomAdapterError):
        return exc
    if isinstance(exc, asyncio.TimeoutError):
        return BoardroomAdapterError("provider_timeout", "Boardroom provider timed out.", status=504,
                                     code="provider_timeout", headers={"X-Causora-Provider-Mode": "unavailable"})
    reason = str(getattr(exc, "reason", "boardroom_pipeline_failed"))
    safe_reason = reason if _SAFE_REASON.fullmatch(reason) else "boardroom_pipeline_failed"
    details = getattr(exc, "details", {})
    failure_reasons = details.get("failureReasons", {}) if isinstance(details, Mapping) else {}
    safe_failures = {
        role: value for role, value in failure_reasons.items()
        if role in {"CFO", "COO", "Risk"} and isinstance(value, str) and _SAFE_REASON.fullmatch(value)
    } if isinstance(failure_reasons, Mapping) else {}
    logging.getLogger(__name__).warning("Boardroom failure reason=%s roleFailures=%s", safe_reason, safe_failures)
    if reason in {"critic_unavailable", "critic_timeout"}:
        return BoardroomAdapterError("critic_unavailable", "Boardroom Critic is unavailable.", status=503,
                                     code="simulation_failed", headers={"X-Causora-Critic-Status": "unavailable"})
    if reason in {"provider_timeout", "timeout", "deadline_exceeded"}:
        return BoardroomAdapterError("provider_timeout", "Boardroom provider timed out.", status=504,
                                     code="provider_timeout", headers={"X-Causora-Provider-Mode": "unavailable"})
    status = getattr(exc, "status", None)
    if status == 422 or reason in {"invalid", "invalid_output", "numeric_guardrail_rejected"}:
        return BoardroomAdapterError(reason if _SAFE_REASON.fullmatch(reason) else "boardroom_result_invalid",
                                     "Boardroom review output is invalid.", status=422, code="validation_error")
    return BoardroomAdapterError(reason if _SAFE_REASON.fullmatch(reason) else "boardroom_pipeline_failed",
                                 "Boardroom review could not produce a validated result.", status=503,
                                 code="simulation_failed")


def _result_parts(result: Any) -> tuple[dict[str, Any], dict[str, str]]:
    envelope = getattr(result, "envelope", None)
    result_headers = getattr(result, "headers", None)
    if isinstance(result, Mapping):
        envelope = result.get("envelope", envelope)
        result_headers = result.get("headers", result_headers)
    if not isinstance(envelope, dict) or not isinstance(result_headers, Mapping):
        raise BoardroomAdapterError("boardroom_result_invalid", "Boardroom review output is invalid.",
                                    status=422, code="validation_error")
    headers: dict[str, str] = {}
    for key, value in result_headers.items():
        if isinstance(key, str) and isinstance(value, str):
            headers[key.lower()] = value
    return _detach(envelope), headers


def _validated_success(envelope: dict[str, Any], *, request_id: str,
                       record: RegisteredSimulation, scenario_id: str) -> dict[str, Any]:
    try:
        validated = BoardroomSuccess.model_validate(envelope).model_dump(mode="json")
    except (ValidationError, ValueError, TypeError) as exc:
        raise BoardroomAdapterError("boardroom_result_invalid", "Boardroom review output is invalid.",
                                    status=422, code="validation_error") from exc
    if (validated["requestId"] != request_id or validated["dataVersion"] != record.data_version or
            validated["data"]["scenarioId"] != scenario_id):
        raise BoardroomAdapterError("boardroom_result_stale", "Boardroom review output is not bound to this simulation request.",
                                    status=422, code="validation_error")
    return validated


async def _run_formal_pipeline(request_dict: dict[str, Any], record: RegisteredSimulation,
                               request_id: str) -> tuple[dict[str, Any], str, str]:
    selection = record.success["data"]["selections"].get(request_dict["scenarioId"])
    if selection and selection["status"] == "no_feasible_option":
        # This branch is derived solely from the already registered, source-
        # verified current Matrix.  It must not import the independently owned
        # AI package, construct a provider, or fabricate a recommendation.
        # The historical pipeline uses the same typed no-feasible envelope and
        # transport labels; they mean no dispatch took place, not AI success.
        envelope = {
            "schemaVersion": SCHEMA_VERSION_V1,
            "dataVersion": record.data_version,
            "requestId": request_id,
            "data": {
                "scenarioId": request_dict["scenarioId"],
                "agentOutputs": [],
                "criticIssues": [],
                "brief": {
                    "scenarioId": request_dict["scenarioId"],
                    "status": "no_feasible_option",
                    "recommendedOptionId": None,
                    "constraintViolations": _thaw(selection["constraintViolations"]),
                    "message": "No simulated option meets the current constraints. Revise inputs and run the simulator again.",
                },
                "numericGuardrail": {"passed": True, "rejectedClaims": []},
            },
        }
        return _validated_success(envelope, request_id=request_id, record=record,
                                  scenario_id=request_dict["scenarioId"]), "primary", "complete"

    inputs_module, pipeline_module, wire_module = _agent_modules()
    runner = getattr(pipeline_module, "run_boardroom", None)
    pipeline_config_type = getattr(wire_module, "PipelineConfig", None)
    if not callable(runner) or not callable(pipeline_config_type):
        raise BoardroomAdapterError("boardroom_pipeline_unavailable", "Boardroom review is not configured.",
                                    status=503, code="simulation_failed")
    run = _make_verified_run(record, inputs_module)
    provider, critic_provider, fallback_provider, config = _load_formal_runtime(pipeline_config_type)
    try:
        result = await runner(request_dict, run=run, provider=provider, critic_provider=critic_provider,
                              fallback_provider=fallback_provider, correlation_id=request_id, config=config)
    except asyncio.CancelledError:
        # Do not catch cancellation: cancelling an HTTP request must cancel the
        # pipeline but it must never remove the immutable simulation record.
        raise
    except Exception as exc:
        raise _pipeline_error(exc) from exc
    finally:
        unique = {id(item): item for item in (provider, critic_provider, fallback_provider) if item is not None}
        async def close_client(item):
            close = getattr(item, "aclose", None)
            if callable(close):
                try:
                    await asyncio.wait_for(close(), timeout=1.0)
                except Exception:
                    pass  # Cleanup errors do not modify a simulation or leak provider details.
        await asyncio.gather(*(close_client(item) for item in unique.values()))
    envelope, result_headers = _result_parts(result)
    provider_mode = result_headers.get("x-causora-provider-mode")
    critic_status = result_headers.get("x-causora-critic-status")
    if critic_status == "unavailable":
        raise BoardroomAdapterError("critic_unavailable", "Boardroom Critic is unavailable.", status=503,
                                    code="simulation_failed", headers={"X-Causora-Critic-Status": "unavailable"})
    if provider_mode not in {"primary", "same-family-fallback"} or critic_status != "complete":
        raise BoardroomAdapterError("boardroom_result_invalid", "Boardroom review output is invalid.",
                                    status=422, code="validation_error")
    return _validated_success(envelope, request_id=request_id, record=record,
                              scenario_id=request_dict["scenarioId"]), provider_mode, critic_status


router = APIRouter()


@router.post("/api/boardroom")
async def boardroom(request: Request, payload: Any = Body(...)) -> JSONResponse:
    """Run Boardroom only for the exact latest reviewed simulation in memory."""
    try:
        request_id = _canonical_request_id(request)
    except BoardroomAdapterError as exc:
        return _failure(exc, f"req-{uuid4().hex}")
    try:
        if not isinstance(payload, dict):
            raise ValueError("object required")
        boardroom_request = BoardroomRequest.model_validate(payload)
    except (ValidationError, ValueError, TypeError):
        return _failure(BoardroomAdapterError("invalid_input", "Invalid Boardroom request.", status=422,
                                              code="validation_error"), request_id)
    try:
        record = repository.resolve_formal(boardroom_request)
        request_dict = boardroom_request.model_dump(mode="json")
        envelope, provider_mode, critic_status = await _run_formal_pipeline(request_dict, record, request_id)
        # A new simulation may arrive while model calls are awaited. Never label
        # the retired record as current merely because it was current at entry.
        repository.resolve_formal(boardroom_request)
        return JSONResponse(
            status_code=200,
            content=envelope,
            headers=_headers(request_id, current_simulation_id=record.simulation_id,
                             provider_mode=provider_mode, critic_status=critic_status),
        )
    except asyncio.CancelledError:
        raise
    except BoardroomAdapterError as exc:
        current_id = exc.headers.get("X-Causora-Current-Simulation") or boardroom_request.simulationId
        return _failure(exc, request_id, current_simulation_id=current_id)


@router.get("/api/evidence/{evidence_id}")
async def evidence(evidence_id: str, request: Request) -> JSONResponse:
    """Return evidence from the repository's current run (the client sends no dataVersion)."""
    try:
        request_id = _canonical_request_id(request)
    except BoardroomAdapterError as exc:
        return _failure(exc, f"req-{uuid4().hex}")
    if evidence_id not in ALLOWED_EVIDENCE_IDS:
        return _failure(BoardroomAdapterError("evidence_not_found", "Evidence record was not found.", status=404,
                                              code="not_found"), request_id)
    try:
        record = repository.current()
        item = record.evidence_record(evidence_id)
        if item is None:
            raise BoardroomAdapterError("evidence_not_found", "Evidence record was not found.", status=404,
                                        code="not_found")
        envelope = {"schemaVersion": SCHEMA_VERSION_V1, "dataVersion": record.data_version,
                    "requestId": request_id, "data": {"evidence": item}}
        validated = EvidenceSuccess.model_validate(envelope).model_dump(mode="json")
        return JSONResponse(status_code=200, content=validated,
                            headers=_headers(request_id, current_simulation_id=record.simulation_id))
    except BoardroomAdapterError as exc:
        return _failure(exc, request_id)
    except (ValidationError, ValueError, TypeError):
        return _failure(BoardroomAdapterError("evidence_invalid", "Evidence record is invalid.", status=503,
                                              code="simulation_failed"), request_id)


def install_boardroom_routes(app: FastAPI) -> None:
    """Install routes once; importing this adapter does not import agent_day4."""
    if getattr(app.state, "boardroom_adapter_routes_installed", False):
        return
    app.include_router(router)
    app.state.boardroom_adapter_routes_installed = True
