"""Dedicated OpenRouter transport for the bounded Day 4 pipeline.

This module deliberately has no legacy generic OpenAI-compatible credential fallback.  It accepts only the
approved OpenRouter model IDs, requires a read-only /models + /key preflight, and makes a
single model dispatch only after an explicit caller authorization.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import math
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Awaitable, Callable

import portalocker

from .provider import ProviderFailure
from .wire import PipelineConfig

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_PROCESS_CALLS = 6
MAX_PROCESS_USD = Decimal("1.00")
MAX_REQUEST_BYTES = 24_000
INPUT_FRAMING_TOKENS = 4_096

# These are the sole approved IDs and price ceilings.  Prices in request.provider.max_price
# are deliberately USD per 1M tokens, as required by this integration's policy.
@dataclass(frozen=True)
class OpenRouterModel:
    model_id: str
    family: str
    prompt_usd_per_token: Decimal
    completion_usd_per_token: Decimal
    needs_max_completion_tokens: bool = False

    @property
    def prompt_usd_per_million(self) -> Decimal:
        return self.prompt_usd_per_token * Decimal(1_000_000)

    @property
    def completion_usd_per_million(self) -> Decimal:
        return self.completion_usd_per_token * Decimal(1_000_000)


MODELS: dict[str, OpenRouterModel] = {
    "openai/gpt-5-mini": OpenRouterModel(
        "openai/gpt-5-mini", "openai-gpt", Decimal("0.00000025"), Decimal("0.000002"), True
    ),
    "google/gemini-3.1-pro-preview": OpenRouterModel(
        "google/gemini-3.1-pro-preview", "google-gemini", Decimal("0.000002"), Decimal("0.000012")
    ),
}
PRIMARY_MODEL = "openai/gpt-5-mini"
CRITIC_MODEL = "google/gemini-3.1-pro-preview"

# Long enough to catch current OpenRouter and standard API-key forms without treating ordinary
# prose such as "sketch" as a credential.  We never include the matched string in an audit.
_SECRET_RE = re.compile(r"(?:sk-or-v1-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9_-]{20,}|rk-[A-Za-z0-9_-]{20,})")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return converted if converted.is_finite() else None


def _contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_SECRET_RE.search(value))
    if isinstance(value, dict):
        return any(_contains_secret(key) or _contains_secret(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_secret(item) for item in value)
    return False


def redact_secrets(value: Any) -> Any:
    """Return a structurally useful value without retaining API-looking strings."""
    if isinstance(value, str):
        return _SECRET_RE.sub("[REDACTED_SECRET]", value)
    if isinstance(value, dict):
        return {str(key): redact_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return value


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _model_spec(model: str) -> OpenRouterModel:
    try:
        return MODELS[model]
    except KeyError:
        raise ProviderFailure("openrouter_model_not_allowed") from None


JOURNAL_KIND = "OPENROUTER_USD_ONE_RESERVATION_JOURNAL"
SAFETY_MARGIN_USD = Decimal("0.05")
JOURNAL_LOCK_TIMEOUT_SECONDS = 5.0


class OpenRouterBudget:
    """Atomic six-call reservation ledger shared safely by independent processes.

    Reservations are deliberately never released.  A request that times out, is cancelled, or
    cannot be marked may have reached the remote provider, so its worst-case reserve remains
    charged.  The optional journal is protected by a *sidecar* portalocker lock; journal files
    themselves are only replaced atomically after their write stream is closed, which works on
    both Windows and POSIX platforms.
    """

    def __init__(self, *, max_calls: int = MAX_PROCESS_CALLS, max_usd: Decimal = MAX_PROCESS_USD, journal_path: Path | None = None):
        configured_cap = _safe_decimal(max_usd)
        if max_calls != MAX_PROCESS_CALLS:
            raise ValueError("OpenRouter request budget is fixed at six calls")
        if configured_cap is None or configured_cap <= 0 or configured_cap > MAX_PROCESS_USD:
            raise ValueError("OpenRouter USD cap must be finite, positive and no more than one")
        self.limit = max_calls
        self.max_usd = configured_cap
        self.used = 0
        self.reserved_usd = Decimal("0")
        self.journal_path = Path(journal_path) if journal_path else None
        self.authorized_usd = MAX_PROCESS_USD
        self.current_available_usd: Decimal | None = None
        self.margin_usd = SAFETY_MARGIN_USD
        self._entries: list[dict[str, Any]] = []
        self._failed_closed = False
        self._lock = asyncio.Lock()

    def set_journal_path(self, path: Path) -> None:
        if self.used or self._entries:
            raise ProviderFailure("openrouter_budget_already_started")
        self.journal_path = Path(path)

    def configure_current_available(self, current_available: Decimal) -> Decimal:
        """Apply the explicit USD-one authorization and non-spendable safety margin."""
        available = _safe_decimal(current_available)
        if available is None or available <= self.margin_usd:
            raise ProviderFailure("openrouter_available_budget_too_small")
        ceiling = min(self.authorized_usd, available) - self.margin_usd
        # A caller may supply a stricter test/local cap; preflight must never loosen it.
        self.max_usd = min(self.max_usd, ceiling)
        self.current_available_usd = available
        return self.max_usd

    @staticmethod
    def _validated_entry(entry: Any) -> dict[str, Any]:
        if not isinstance(entry, dict):
            raise ProviderFailure("openrouter_budget_journal_invalid")
        reserved = _safe_decimal(entry.get("reservedUsd"))
        if reserved is None or reserved < 0:
            raise ProviderFailure("openrouter_budget_journal_invalid")
        if "verifiedCostUsd" in entry:
            verified = _safe_decimal(entry["verifiedCostUsd"])
            if verified is None or verified < 0:
                raise ProviderFailure("openrouter_budget_journal_invalid")
        return entry

    @classmethod
    def _journal_total(cls, entries: list[dict[str, Any]]) -> Decimal:
        """Return the conservative committed amount, including verified cost overruns."""
        total = Decimal("0")
        for raw_entry in entries:
            entry = cls._validated_entry(raw_entry)
            reserved = _safe_decimal(entry["reservedUsd"])
            assert reserved is not None
            verified = _safe_decimal(entry["verifiedCostUsd"]) if "verifiedCostUsd" in entry else None
            total += max(reserved, verified) if verified is not None else reserved
        return total

    @staticmethod
    def _read_journal_path(path: Path) -> dict[str, Any]:
        """Read only a complete journal.  A precisely empty legacy file is safe to initialise.

        Atomic writes used below never leave an empty journal.  Supporting an exactly empty file
        retains compatibility with the previous ``a+`` implementation, while whitespace-only,
        malformed, or entries-missing files fail closed rather than being reset.
        """
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"kind": JOURNAL_KIND, "entries": []}
        except (OSError, UnicodeError):
            raise ProviderFailure("openrouter_budget_journal_unavailable") from None
        if raw == "":
            return {"kind": JOURNAL_KIND, "entries": []}
        if not raw.strip():
            raise ProviderFailure("openrouter_budget_journal_invalid")
        try:
            journal = json.loads(raw)
        except (TypeError, ValueError):
            raise ProviderFailure("openrouter_budget_journal_invalid") from None
        if not isinstance(journal, dict) or journal.get("kind") != JOURNAL_KIND or not isinstance(journal.get("entries"), list):
            raise ProviderFailure("openrouter_budget_journal_invalid")
        for entry in journal["entries"]:
            OpenRouterBudget._validated_entry(entry)
        return journal

    @staticmethod
    def _atomic_write_journal(path: Path, journal: dict[str, Any]) -> None:
        """Fsync a same-directory temp file then replace only after its handle is closed."""
        descriptor = None
        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
            os.chmod(temporary_name, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = None
                json.dump(journal, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            # The target journal stream is not open anywhere in this implementation.  Closing
            # before os.replace is required for the Windows replacement semantics.
            os.replace(temporary_name, path)
            temporary_name = None
            if os.name != "nt":
                directory_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except (OSError, TypeError, ValueError):
            raise ProviderFailure("openrouter_budget_journal_unavailable") from None
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name)
                except OSError:
                    pass

    def _new_metadata(self, ceiling: Decimal) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "authorizedUsd": str(self.authorized_usd),
            "currentCeiling": str(ceiling),
            "margin": str(self.margin_usd),
        }
        if self.current_available_usd is not None:
            metadata["currentAvailableUsd"] = str(self.current_available_usd)
        return metadata

    def _reconcile_metadata(self, journal: dict[str, Any]) -> tuple[Decimal, bool]:
        """Return the non-expandable journal ceiling and whether metadata changed."""
        metadata = journal.get("metadata")
        if metadata is None:
            journal["metadata"] = self._new_metadata(self.max_usd)
            return self.max_usd, True
        if not isinstance(metadata, dict):
            raise ProviderFailure("openrouter_budget_journal_invalid")
        persistent_ceiling = _safe_decimal(metadata.get("currentCeiling"))
        authorized = _safe_decimal(metadata.get("authorizedUsd"))
        margin = _safe_decimal(metadata.get("margin"))
        if (
            persistent_ceiling is None
            or persistent_ceiling <= 0
            or persistent_ceiling > MAX_PROCESS_USD
            or authorized is None
            or authorized <= 0
            or authorized > MAX_PROCESS_USD
            or margin != SAFETY_MARGIN_USD
            or ("overCap" in metadata and not isinstance(metadata["overCap"], bool))
        ):
            raise ProviderFailure("openrouter_budget_journal_invalid")
        effective_ceiling = min(self.max_usd, persistent_ceiling)
        changed = False
        if effective_ceiling < persistent_ceiling:
            # Later processes may report more remote credit, but they can only tighten—not
            # expand—the ceiling originally committed to this shared journal.
            metadata["currentCeiling"] = str(effective_ceiling)
            changed = True
        if self.current_available_usd is not None:
            prior_available = _safe_decimal(metadata.get("currentAvailableUsd")) if "currentAvailableUsd" in metadata else None
            stored_available = min(prior_available, self.current_available_usd) if prior_available is not None else self.current_available_usd
            if metadata.get("currentAvailableUsd") != str(stored_available):
                metadata["currentAvailableUsd"] = str(stored_available)
                changed = True
        return effective_ceiling, changed

    def _locked_journal_transaction(self, action: Callable[[dict[str, Any]], tuple[Any, bool]]) -> Any:
        assert self.journal_path is not None
        path = self.journal_path
        lock_path = path.with_name(path.name + ".lock")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with portalocker.Lock(str(lock_path), mode="a+", timeout=JOURNAL_LOCK_TIMEOUT_SECONDS, check_interval=0.05):
                try:
                    os.chmod(lock_path, 0o600)
                except OSError:
                    raise ProviderFailure("openrouter_budget_journal_unavailable") from None
                journal = self._read_journal_path(path)
                result, write = action(journal)
                if write:
                    self._atomic_write_journal(path, journal)
                return result
        except ProviderFailure:
            raise
        except portalocker.exceptions.LockException:
            raise ProviderFailure("openrouter_budget_journal_lock_timeout") from None
        except OSError:
            raise ProviderFailure("openrouter_budget_journal_unavailable") from None

    @staticmethod
    def _safe_status(status: str) -> str:
        if not isinstance(status, str) or not re.fullmatch(r"[A-Za-z0-9_:-]{1,128}", status) or _contains_secret(status):
            raise ValueError("reservation status must be a non-secret identifier")
        return status

    def _apply_entries(self, entries: list[dict[str, Any]]) -> None:
        self.used = len(entries)
        self.reserved_usd = self._journal_total(entries)

    def _reserve_persistently(self, entry: dict[str, Any], amount: Decimal) -> tuple[int, Decimal, Decimal]:
        """Append and commit a reservation while holding the cross-platform sidecar lock."""
        def action(journal: dict[str, Any]) -> tuple[tuple[int, Decimal, Decimal], bool]:
            ceiling, metadata_changed = self._reconcile_metadata(journal)
            entries = journal["entries"]
            committed = self._journal_total(entries)
            metadata = journal["metadata"]
            if len(entries) >= self.limit:
                raise ProviderFailure("provider_call_budget_exhausted")
            if metadata.get("overCap") is True or committed > ceiling or committed + amount > ceiling:
                raise ProviderFailure("openrouter_usd_budget_exhausted")
            entries.append(entry)
            return (len(entries), committed + amount, ceiling), True or metadata_changed

        return self._locked_journal_transaction(action)

    async def reserve(self, *, stage: str, model: str, amount: Decimal, input_bound: int, max_output_tokens: int) -> str:
        normalized_amount = _safe_decimal(amount)
        if normalized_amount is None or normalized_amount < 0:
            raise ValueError("reservation must be finite and non-negative")
        reservation_id = uuid.uuid4().hex
        entry = {
            "reservationId": reservation_id,
            "reservedAtUtc": _utc_now(),
            "stage": stage,
            "model": model,
            "reservedUsd": str(normalized_amount),
            "maxInputTokensBound": input_bound,
            "maxOutputTokens": max_output_tokens,
            "status": "reserved_unknown_remote_cost",
        }
        async with self._lock:
            if self._failed_closed:
                raise ProviderFailure("openrouter_budget_journal_unavailable")
            if self.journal_path is None:
                if self.used >= self.limit:
                    raise ProviderFailure("provider_call_budget_exhausted")
                if self.reserved_usd + normalized_amount > self.max_usd:
                    raise ProviderFailure("openrouter_usd_budget_exhausted")
                self._entries.append(entry)
                self._apply_entries(self._entries)
            else:
                try:
                    used, committed, ceiling = await asyncio.to_thread(self._reserve_persistently, entry, normalized_amount)
                except ProviderFailure as exc:
                    if exc.reason in {"openrouter_budget_journal_unavailable", "openrouter_budget_journal_lock_timeout"}:
                        self._failed_closed = True
                    raise
                self.used = used
                self.reserved_usd = committed
                self.max_usd = min(self.max_usd, ceiling)
        return reservation_id

    def _mark_persistently(self, reservation_id: str, status: str, verified_cost: Decimal | None) -> tuple[int, Decimal, Decimal]:
        assert self.journal_path is not None

        def action(journal: dict[str, Any]) -> tuple[tuple[int, Decimal, Decimal], bool]:
            ceiling, metadata_changed = self._reconcile_metadata(journal)
            entries = journal["entries"]
            entry = next((item for item in entries if item.get("reservationId") == reservation_id), None)
            if entry is None:
                raise ProviderFailure("openrouter_budget_journal_invalid")
            entry["status"] = status
            entry["finalizedAtUtc"] = _utc_now()
            if verified_cost is not None:
                previous_cost = _safe_decimal(entry.get("verifiedCostUsd"))
                entry["verifiedCostUsd"] = str(max(previous_cost, verified_cost) if previous_cost is not None else verified_cost)
            committed = self._journal_total(entries)
            if committed > ceiling:
                journal["metadata"]["overCap"] = True
            return (len(entries), committed, ceiling), True or metadata_changed

        return self._locked_journal_transaction(action)

    async def mark(self, reservation_id: str, status: str, verified_cost: Decimal | None = None) -> None:
        safe_status = self._safe_status(status)
        normalized_verified = None if verified_cost is None else _safe_decimal(verified_cost)
        if verified_cost is not None and (normalized_verified is None or normalized_verified < 0):
            raise ValueError("verified cost must be finite and non-negative")
        async with self._lock:
            if self.journal_path is None:
                entry = next((item for item in self._entries if item.get("reservationId") == reservation_id), None)
                if entry is None:
                    raise ProviderFailure("openrouter_budget_journal_invalid")
                entry["status"] = safe_status
                entry["finalizedAtUtc"] = _utc_now()
                if normalized_verified is not None:
                    previous_cost = _safe_decimal(entry.get("verifiedCostUsd"))
                    entry["verifiedCostUsd"] = str(max(previous_cost, normalized_verified) if previous_cost is not None else normalized_verified)
                self._apply_entries(self._entries)
                return
            try:
                used, committed, ceiling = await asyncio.to_thread(self._mark_persistently, reservation_id, safe_status, normalized_verified)
            except ProviderFailure:
                # The reservation is already durable and conservative.  Do not report an
                # apparently successful remote completion when its durable finalization failed.
                self._failed_closed = True
                raise
            self.used = used
            self.reserved_usd = committed
            self.max_usd = min(self.max_usd, ceiling)

    @classmethod
    def _snapshot_payload(cls, entries: list[dict[str, Any]], ceiling: Decimal) -> dict[str, Any]:
        verified_total = Decimal("0")
        unknown_total = Decimal("0")
        unknown_count = 0
        unknown_entries: list[dict[str, Any]] = []
        for raw_entry in entries:
            entry = cls._validated_entry(raw_entry)
            verified = _safe_decimal(entry["verifiedCostUsd"]) if "verifiedCostUsd" in entry else None
            if verified is None:
                unknown_count += 1
                reserved = _safe_decimal(entry["reservedUsd"])
                assert reserved is not None
                unknown_total += reserved
                unknown_entries.append({
                    "reservationId": entry.get("reservationId"),
                    "reservedUsd": str(reserved),
                    "status": entry.get("status"),
                })
            else:
                verified_total += verified
        # JSON round-tripping returns an independent, JSON-only read model to callers.
        safe_entries = json.loads(json.dumps(entries, ensure_ascii=False, allow_nan=False))
        return {
            "entries": safe_entries,
            "callCount": len(entries),
            "conservativeCommittedUsd": str(cls._journal_total(entries)),
            "verifiedCostUsd": str(verified_total),
            "unknownCosts": {"count": unknown_count, "conservativeReservedUsd": str(unknown_total)},
            "unknownRemoteEntries": unknown_entries,
            "usageTotals": {
                "callCount": len(entries),
                "conservativeCommittedUsd": str(cls._journal_total(entries)),
                "verifiedCostUsd": str(verified_total),
                "unknownRemoteReservedUsd": str(unknown_total),
            },
            "currentCeilingUsd": str(ceiling),
        }

    def snapshot(self) -> dict[str, Any]:
        """Read a locked shared-ledger total; callers must not reconstruct cost from audits."""
        if self.journal_path is None:
            self._apply_entries(self._entries)
            return self._snapshot_payload(self._entries, self.max_usd)

        def action(journal: dict[str, Any]) -> tuple[tuple[list[dict[str, Any]], Decimal], bool]:
            ceiling, metadata_changed = self._reconcile_metadata(journal)
            entries = journal["entries"]
            return (entries, ceiling), metadata_changed

        entries, ceiling = self._locked_journal_transaction(action)
        self._apply_entries(entries)
        self.max_usd = min(self.max_usd, ceiling)
        return self._snapshot_payload(entries, ceiling)


class OpenRouterSession:
    """Shared OpenRouter client, preflight state, and process budget for all three roles."""

    def __init__(
        self,
        *,
        api_key: str,
        config: PipelineConfig,
        client: Any | None = None,
        http_get: Callable[[str], Awaitable[dict[str, Any]] | dict[str, Any]] | None = None,
        budget: OpenRouterBudget | None = None,
    ):
        if not api_key:
            raise ProviderFailure("openrouter_not_configured")
        self._api_key = api_key
        self.config = config
        if client is None:
            from openai import AsyncOpenAI
            # Per-call with_options(timeout=...) below receives the exact pipeline deadline.
            client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, max_retries=0, timeout=config.critic_timeout)
        self.client = client
        self._http_get = http_get or self._remote_get
        self.budget = budget or OpenRouterBudget()
        self.preflight_summary: dict[str, Any] | None = None
        self._authorized = False
        self._closed = False
        self._close_lock = asyncio.Lock()

    async def _remote_get(self, path: str) -> dict[str, Any]:
        # GET preflight calls use only the dedicated OpenRouter key and never put headers,
        # labels, or response bodies into an audit record.
        import httpx

        async with httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={"Authorization": "Bearer " + self._api_key},
            timeout=self.config.stage_timeout,
        ) as http:
            response = await http.get(path)
            response.raise_for_status()
            result = response.json()
        if not isinstance(result, dict):
            raise ProviderFailure("openrouter_preflight_invalid_response")
        return result

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            value = self._http_get(path)
            if inspect.isawaitable(value):
                value = await value
        except ProviderFailure:
            raise
        except Exception:
            raise ProviderFailure("openrouter_preflight_request_failed") from None
        if not isinstance(value, dict):
            raise ProviderFailure("openrouter_preflight_invalid_response")
        return value

    @staticmethod
    def _validate_models(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
        rows = document.get("data")
        if not isinstance(rows, list):
            raise ProviderFailure("openrouter_models_preflight_invalid")
        found: dict[str, dict[str, Any]] = {}
        required_common = {"response_format", "structured_outputs", "reasoning", "max_tokens"}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                continue
            model_id = row["id"]
            if model_id not in MODELS:
                continue
            supported = row.get("supported_parameters")
            if not isinstance(supported, list) or not all(isinstance(item, str) for item in supported):
                raise ProviderFailure("openrouter_model_unsupported")
            needed = set(required_common)
            if MODELS[model_id].needs_max_completion_tokens:
                needed.add("max_completion_tokens")
            if not needed.issubset(set(supported)):
                raise ProviderFailure("openrouter_model_unsupported")
            pricing=row.get('pricing')
            if not isinstance(pricing,dict):raise ProviderFailure('openrouter_model_price_unverified')
            prompt=_safe_decimal(pricing.get('prompt'));completion=_safe_decimal(pricing.get('completion'))
            spec=MODELS[model_id]
            if prompt is None or completion is None or prompt<0 or completion<0:
                raise ProviderFailure('openrouter_model_price_unverified')
            if prompt>spec.prompt_usd_per_token or completion>spec.completion_usd_per_token:
                raise ProviderFailure('openrouter_model_price_exceeds_cap')
            found[model_id] = row
        missing = set(MODELS) - set(found)
        if missing:
            raise ProviderFailure("openrouter_model_not_available")
        return found

    @staticmethod
    def _validate_key(document: dict[str, Any]) -> dict[str, Any]:
        data = document.get("data")
        if not isinstance(data, dict):
            raise ProviderFailure("openrouter_key_limit_missing")
        required = ("limit", "usage", "limit_remaining", "limit_reset", "include_byok_in_limit")
        if any(name not in data for name in required):
            raise ProviderFailure("openrouter_key_limit_missing")
        limit = _safe_decimal(data["limit"])
        usage = _safe_decimal(data["usage"])
        remaining = _safe_decimal(data["limit_remaining"])
        if limit is None or usage is None or remaining is None:
            raise ProviderFailure("openrouter_key_limit_invalid")
        # Historical account usage and a remaining allowance above USD one are both legitimate.
        # The independent one-dollar authorization is applied to dispatch later; /key must only
        # prove a finite, positive, non-resetting and internally consistent available amount.
        if not (limit > 0 and usage >= 0 and remaining > 0):
            raise ProviderFailure("openrouter_key_limit_invalid")
        if abs((limit - usage) - remaining) > Decimal("0.000001"):
            raise ProviderFailure("openrouter_key_limit_invalid")
        # A reset would permit spend beyond the explicit authorization; null is required.
        if data["limit_reset"] is not None:
            raise ProviderFailure("openrouter_key_limit_reset_not_null")
        if not isinstance(data["include_byok_in_limit"], bool):
            raise ProviderFailure("openrouter_key_limit_invalid")
        # Return only non-secret, read-only account state needed for the evidence manifest.
        return {
            "limitUsd": str(limit),
            "usageUsd": str(usage),
            "limitRemainingUsd": str(remaining),
            "limitReset": None,
            "includeByokInLimit": data["include_byok_in_limit"],
            "byokCostAccounting": (
                "INCLUDED_IN_KEY_LIMIT" if data["include_byok_in_limit"]
                else "NOT_INCLUDED_IN_KEY_LIMIT; NO_BYOK_PARAMETERS_OR_KEYS_ARE_PERMITTED"
            ),
        }

    async def preflight(self) -> dict[str, Any]:
        """Read /models then /key.  This never creates a chat completion request."""
        models_document = await self._get("/models")
        models = self._validate_models(models_document)
        key_document = await self._get("/key")
        key = self._validate_key(key_document)
        ceiling = self.budget.configure_current_available(Decimal(key["limitRemainingUsd"]))
        self.preflight_summary = {
            "checkedAtUtc": _utc_now(),
            "baseUrl": OPENROUTER_BASE_URL,
            "models": {
                model_id: {
                    "supportedParameters": sorted(models[model_id]["supported_parameters"]),
                    "catalogPricingUsdPerToken":{k:models[model_id]['pricing'][k]for k in ('prompt','completion')},
                    "priceCapsUsdPer1M": {
                        "prompt": str(spec.prompt_usd_per_million),
                        "completion": str(spec.completion_usd_per_million),
                    },
                }
                for model_id, spec in MODELS.items()
            },
            "key": key,
            "budget": {
                "authorizedUsd": str(self.budget.authorized_usd),
                "currentAvailableUsd": key["limitRemainingUsd"],
                "safetyMarginUsd": str(self.budget.margin_usd),
                "currentCeilingUsd": str(ceiling),
            },
        }
        return dict(self.preflight_summary)

    def authorize(self, *, scoped_key_confirmed: bool=False, fresh_dedicated_key_confirmed: bool=False) -> None:
        if self.preflight_summary is None:
            raise ProviderFailure("openrouter_preflight_required")
        if not (scoped_key_confirmed or fresh_dedicated_key_confirmed):
            raise ProviderFailure("openrouter_scoped_key_confirmation_required")
        self._authorized = True

    def require_dispatch_authorization(self) -> None:
        if self.preflight_summary is None:
            raise ProviderFailure("openrouter_preflight_required")
        if not self._authorized:
            raise ProviderFailure("openrouter_paid_dispatch_not_authorized")

    async def aclose(self) -> None:
        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            close = getattr(self.client, "close", None)
            if close is not None:
                result = close()
                if inspect.isawaitable(result):
                    await result


class OpenRouterProvider:
    """A role provider with a fixed OpenRouter model and a shared session budget."""

    kind = "LIVE_PROVIDER"
    supports_request_timeout = True

    def __init__(self, model: str, *, session: OpenRouterSession, config: PipelineConfig | None = None, timeout: float | None = None):
        self.spec = _model_spec(model)
        self.model = model
        self.family = self.spec.family
        self.session = session
        self.config = config or session.config
        self.sdk_timeout = self._valid_timeout(self.config.critic_timeout if timeout is None else timeout, "SDK timeout")
        self.budget = session.budget
        self.max_calls = self.budget.limit
        self.calls = 0
        self.audit: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    @staticmethod
    def _valid_timeout(value: float | int, description: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(description + " must be a finite positive number")
        return float(value)

    def _request_timeout(self, stage: str, request_timeout: float | None) -> float:
        if request_timeout is not None:
            return self._valid_timeout(request_timeout, "request_timeout")
        configured = self.config.critic_timeout if stage.casefold() == "critic" else self.config.stage_timeout
        return self._valid_timeout(configured, "configured request timeout")

    @staticmethod
    def _max_output_tokens(stage: str) -> int:
        return 4096 if stage.casefold() == "critic" else 2048

    def _reasoning_effort(self, stage: str) -> str:
        # OpenRouter's unified reasoning.effort is used.  Gemini Critic deliberately does
        # not also receive reasoning.max_tokens or a provider-native thinking-token override.
        return "low" if self.family == "google-gemini" and stage.casefold() == "critic" else "minimal"

    def _parameters(self, *, stage: str, body: str, schema: dict[str, Any], system: str) -> tuple[dict[str, Any], int, int, Decimal]:
        if _contains_secret((body, schema, system)):
            raise ProviderFailure("openrouter_input_secret_rejected")
        # Google's OpenRouter endpoint rejects this strict schema subset. Request JSON
        # and provide the complete schema as instructions; local Pydantic remains the
        # authoritative strict validator (no missing/extra fields are accepted).
        if self.family == "google-gemini":
            system += "\nReturn a JSON object matching this exact schema. Include every required property. " + _json_bytes(schema).decode("utf-8")
        serialized_schema = _json_bytes(schema)
        input_bytes = len(body.encode("utf-8")) + len(serialized_schema) + len(system.encode("utf-8"))
        if input_bytes > MAX_REQUEST_BYTES:
            raise ProviderFailure("openrouter_request_too_large")
        input_bound = input_bytes + INPUT_FRAMING_TOKENS
        max_output = self._max_output_tokens(stage)
        reserved = self.spec.prompt_usd_per_token * Decimal(input_bound) + self.spec.completion_usd_per_token * Decimal(max_output)
        provider_policy = {
            "require_parameters": True,
            "allow_fallbacks": False,
            "max_price": {
                "prompt": float(self.spec.prompt_usd_per_million),
                "completion": float(self.spec.completion_usd_per_million),
            },
        }
        # provider/reasoning/plugins are OpenRouter-specific top-level extensions; OpenAI's
        # SDK transports them through extra_body.  There are intentionally no tools, search,
        # web, routing, or plugin requests, and plugins is explicitly empty.
        parameters = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": body}],
            "max_tokens": max_output,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "causora_" + stage.lower(), "strict": True, "schema": schema},
            },
            "extra_body": {
                "provider": provider_policy,
                "reasoning": {"effort": self._reasoning_effort(stage)},
                "plugins": [],
            },
        }
        if self.family == "google-gemini":
            parameters["response_format"] = {"type": "json_object"}
        return parameters, input_bytes, input_bound, reserved

    @staticmethod
    def _usage_dict(response: Any) -> dict[str, Any] | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        if hasattr(usage, "model_dump"):
            value = usage.model_dump()
        elif isinstance(usage, dict):
            value = usage
        else:
            return None
        return value if isinstance(value, dict) else None

    async def complete(self, *, stage: str, payload: dict[str, Any], schema: dict[str, Any], system: str, request_timeout: float | None = None) -> dict:
        self.session.require_dispatch_authorization()
        effective_timeout = self._request_timeout(stage, request_timeout)
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
        parameters, input_bytes, input_bound, reserved = self._parameters(stage=stage, body=body, schema=schema, system=system)
        started_monotonic = time.monotonic()
        record: dict[str, Any] = {
            "source": "OPENROUTER_HTTPS_API",
            "status": "reservation_pending",
            "stage": stage,
            "providerFamily": self.family,
            "requestedModel": self.model,
            "returnedModel": None,
            "providerReturned": None,
            "requestId": None,
            "startedAtUtc": _utc_now(),
            "inputSha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "schemaSha256": hashlib.sha256(_json_bytes(schema)).hexdigest(),
            "exactSdkDeadlineSeconds": effective_timeout,
            "sdkTimeoutSeconds": effective_timeout,
            "maxInputBytes": input_bytes,
            "maxInputTokensBound": input_bound,
            "maxOutputTokens": self._max_output_tokens(stage),
            "reasoningEffort": self._reasoning_effort(stage),
            "reservedUsd": str(reserved),
            # Until the response supplies usage.cost, neither a successful call nor a timeout
            # is evidence of the exact OpenRouter charge.
            "usageCostStatus": "Unverified",
            "priceCapsUsdPer1M": {
                "prompt": str(self.spec.prompt_usd_per_million),
                "completion": str(self.spec.completion_usd_per_million),
            },
        }
        self.audit.append(record)
        reservation_id: str | None = None
        try:
            async with self._lock:
                # The shared session ledger is the race-safe guard across concurrent role calls.
                reservation_id = await self.budget.reserve(
                    stage=stage, model=self.model, amount=reserved, input_bound=input_bound, max_output_tokens=self._max_output_tokens(stage)
                )
                self.calls += 1
            record["reservationId"] = reservation_id
            record["status"] = "started"
            response = await self.session.client.with_options(timeout=effective_timeout).chat.completions.create(**parameters)
            record['returnedModel']=redact_secrets(getattr(response,'model',None))
            record['providerReturned']=redact_secrets(getattr(response,'provider',None))
            record['requestId']=redact_secrets(getattr(response,'id',None))
            usage=self._usage_dict(response)
            if usage is not None:record['tokenUsage']=redact_secrets(usage)
            verified_cost=_safe_decimal(usage.get('cost')) if usage else None
            if verified_cost is not None and verified_cost>=0:
                record['usageCostUsd']=str(verified_cost);record['usageCostStatus']='VERIFIED_OPENROUTER_USAGE_COST'
                if verified_cost>reserved:
                    self.session._authorized=False
                    raise ProviderFailure('openrouter_cost_exceeded_reservation')
            if record['returnedModel']!=self.model:raise ProviderFailure('openrouter_model_return_mismatch')
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content:
                raise ProviderFailure("provider_empty_response")
            record["outputSha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            # Never preserve raw content or a parsed equivalent when it appears to contain a key.
            if _contains_secret(content):
                record["status"] = "provider_secret_output_rejected"
                record["outputSecretRejected"] = True
                raise ProviderFailure("provider_secret_output_rejected")
            try:
                value = json.loads(content)
            except (TypeError, ValueError):
                raise ProviderFailure("provider_malformed_response") from None
            if not isinstance(value, dict):
                raise ProviderFailure("provider_malformed_response")
            if _contains_secret(value):
                record["status"] = "provider_secret_output_rejected"
                record["outputSecretRejected"] = True
                raise ProviderFailure("provider_secret_output_rejected")
            # Parsed data are retained only after secret scanning.  The raw text itself is never
            # audited; the SHA-256 above is the evidence for the exact returned byte sequence.
            record["rawParsedOutput"] = redact_secrets(value)
            record["parsedOutput"] = record["rawParsedOutput"]
            record["status"] = "returned"
            await self.budget.mark(reservation_id, "returned", verified_cost)
            return value
        except asyncio.CancelledError:
            record["status"] = "cancelled"
            if reservation_id:
                await self.budget.mark(reservation_id, "cancelled_unknown_remote_cost")
            raise
        except ProviderFailure as exc:
            if record["status"] in {"reservation_pending", "started"}:
                record["status"] = exc.reason
            if reservation_id:
                await self.budget.mark(reservation_id, record["status"],_safe_decimal(record.get('usageCostUsd')))
            raise
        except Exception as exc:
            safe = {
                "RateLimitError": "provider_rate_limited",
                "APITimeoutError": "provider_timeout",
                "AuthenticationError": "provider_authentication_failed",
                "BadRequestError": "provider_bad_request",
            }
            record["status"] = safe.get(type(exc).__name__, "provider_unavailable")
            if reservation_id:
                await self.budget.mark(reservation_id, record["status"])
            # Do not stringify exceptions: SDK errors may echo request content or credentials.
            raise ProviderFailure(record["status"]) from None
        finally:
            record["elapsedSeconds"] = round(time.monotonic() - started_monotonic, 6)

    async def aclose(self) -> None:
        await self.session.aclose()


def _env_exact(name: str, expected: str) -> None:
    configured = os.getenv(name)
    if configured is not None and configured.strip() and configured.strip() != expected:
        raise ProviderFailure("openrouter_model_not_allowed")


def _env_int_exact(name: str, expected: int) -> None:
    configured = os.getenv(name)
    if configured is None or not configured.strip():
        return
    try:
        parsed = int(configured)
    except ValueError:
        raise ProviderFailure("openrouter_configuration_invalid") from None
    if parsed != expected:
        raise ProviderFailure("openrouter_configuration_invalid")


def providers_from_openrouter_env():
    """Build the explicit OpenRouter trio without touching generic OpenAI-compatible env vars."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ProviderFailure("openrouter_not_configured")
    _env_exact("CAUSORA_PRIMARY_MODEL", PRIMARY_MODEL)
    _env_exact("CAUSORA_GEMINI_CRITIC_MODEL", CRITIC_MODEL)
    _env_exact("CAUSORA_FALLBACK_CRITIC_MODEL", PRIMARY_MODEL)
    _env_int_exact("CAUSORA_AI_MAX_CALLS", MAX_PROCESS_CALLS)
    _env_int_exact("CAUSORA_AI_PIPELINE_CALLS", MAX_PROCESS_CALLS)
    retries = os.getenv("CAUSORA_AI_RETRIES")
    if retries is not None and retries.strip() not in {"", "0"}:
        raise ProviderFailure("openrouter_retries_must_be_zero")
    defaults = PipelineConfig()
    # Preserve bounded timeout controls but force no pipeline retries and the six-call whole-run cap.
    config = PipelineConfig(
        total_timeout=float(os.getenv("CAUSORA_AI_TOTAL_TIMEOUT", str(defaults.total_timeout))),
        stage_timeout=float(os.getenv("CAUSORA_AI_STAGE_TIMEOUT", str(defaults.stage_timeout))),
        critic_timeout=float(os.getenv("CAUSORA_CRITIC_TIMEOUT", str(defaults.critic_timeout))),
        retries=0,
        max_calls=MAX_PROCESS_CALLS,
    )
    session = OpenRouterSession(api_key=api_key, config=config)
    primary = OpenRouterProvider(PRIMARY_MODEL, session=session, config=config, timeout=config.stage_timeout)
    critic = OpenRouterProvider(CRITIC_MODEL, session=session, config=config, timeout=config.critic_timeout)
    fallback = OpenRouterProvider(PRIMARY_MODEL, session=session, config=config, timeout=config.critic_timeout)
    return primary, critic, fallback, config
