"""Local-only OpenRouter USD-one journal portability tests.

These tests exercise actual portalocker sidecar locks on the Ubuntu runner.  They deliberately
make no claim that a Windows host was executed; portalocker is used because it supplies the real
Windows lock implementation when this same code runs there.
"""
from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from queue import Empty

import portalocker
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = PROJECT_ROOT / "agents" / "wanghao-day3"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from agent_day4.openrouter_provider import (  # noqa: E402
    JOURNAL_LOCK_TIMEOUT_SECONDS,
    PRIMARY_MODEL,
    OpenRouterBudget,
)
from agent_day4.provider import ProviderFailure  # noqa: E402


def _reservation_kwargs(amount: Decimal) -> dict:
    return {
        "stage": "local_test",
        "model": PRIMARY_MODEL,
        "amount": amount,
        "input_bound": 1,
        "max_output_tokens": 1,
    }


def _spawn_reservation_worker(journal_name: str, amount_text: str, start, results) -> None:
    """Top-level spawn target: works on Windows instead of relying on POSIX fork state."""
    start.wait(15)
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=Path(journal_name))
    try:
        asyncio.run(budget.reserve(**_reservation_kwargs(Decimal(amount_text))))
    except ProviderFailure as exc:
        results.put((False, exc.reason))
    else:
        results.put((True, "reserved"))


def _spawn_lock_holder(lock_name: str, acquired, release) -> None:
    """Hold the real sidecar lock from another process for timeout validation."""
    with portalocker.Lock(lock_name, mode="a+", timeout=10, check_interval=0.02):
        acquired.set()
        release.wait(20)


def _drain_results(results, count: int) -> list[tuple[bool, str]]:
    values: list[tuple[bool, str]] = []
    for _ in range(count):
        try:
            values.append(results.get(timeout=20))
        except Empty as exc:  # pragma: no cover - diagnostic only on a broken process runtime
            raise AssertionError("spawn reservation worker did not report") from exc
    return values


def test_actual_sidecar_lock_spawn_processes_allow_exactly_six_calls(tmp_path):
    """Twelve independently spawned Python processes contend for six durable call slots."""
    context = mp.get_context("spawn")
    journal = tmp_path / "shared.json"
    start = context.Event()
    results = context.Queue()
    workers = [
        context.Process(target=_spawn_reservation_worker, args=(str(journal), "0.01", start, results))
        for _ in range(12)
    ]
    for worker in workers:
        worker.start()
    start.set()
    values = _drain_results(results, len(workers))
    for worker in workers:
        worker.join(20)
        assert worker.exitcode == 0

    assert sum(success for success, _ in values) == 6
    assert sum(reason == "provider_call_budget_exhausted" for success, reason in values if not success) == 6
    snapshot = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal).snapshot()
    assert snapshot["callCount"] == 6
    assert snapshot["conservativeCommittedUsd"] == "0.06"
    assert len(snapshot["entries"]) == 6


def test_async_and_thread_safe_shared_amount_cap_uses_decimal_floor(tmp_path):
    journal = tmp_path / "amount.json"
    amount = Decimal("0.21")
    cap = Decimal("0.95")
    expected = int(cap // amount)

    async def contend():
        budget = OpenRouterBudget(max_usd=cap, journal_path=journal)
        values = await asyncio.gather(
            *(budget.reserve(**_reservation_kwargs(amount)) for _ in range(12)),
            return_exceptions=True,
        )
        return values

    results = asyncio.run(contend())
    assert sum(isinstance(value, str) for value in results) == expected
    assert sum(isinstance(value, ProviderFailure) for value in results) == 12 - expected
    snapshot = OpenRouterBudget(max_usd=cap, journal_path=journal).snapshot()
    assert snapshot["callCount"] == expected
    assert snapshot["conservativeCommittedUsd"] == str(amount * expected)

    thread_journal = tmp_path / "thread-amount.json"

    def reserve_from_thread() -> bool:
        thread_budget = OpenRouterBudget(max_usd=cap, journal_path=thread_journal)
        try:
            asyncio.run(thread_budget.reserve(**_reservation_kwargs(amount)))
        except ProviderFailure:
            return False
        return True

    with ThreadPoolExecutor(max_workers=12) as executor:
        thread_results = list(executor.map(lambda _unused: reserve_from_thread(), range(12)))
    assert sum(thread_results) == expected
    assert OpenRouterBudget(max_usd=cap, journal_path=thread_journal).snapshot()["callCount"] == expected


def test_new_instance_inherits_calls_spend_metadata_and_never_expands_ceiling(tmp_path):
    journal = tmp_path / "inherit.json"
    first = OpenRouterBudget(max_usd=Decimal("0.50"), journal_path=journal)
    asyncio.run(first.reserve(**_reservation_kwargs(Decimal("0.10"))))
    assert first.snapshot()["currentCeilingUsd"] == "0.50"

    later = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
    with pytest.raises(ProviderFailure, match="openrouter_usd_budget_exhausted"):
        asyncio.run(later.reserve(**_reservation_kwargs(Decimal("0.45"))))
    asyncio.run(later.reserve(**_reservation_kwargs(Decimal("0.40"))))

    snapshot = later.snapshot()
    assert snapshot["callCount"] == 2
    assert snapshot["conservativeCommittedUsd"] == "0.50"
    assert snapshot["currentCeilingUsd"] == "0.50"
    raw = json.loads(journal.read_text(encoding="utf-8"))
    assert raw["metadata"] == {
        "authorizedUsd": "1.00",
        "currentCeiling": "0.50",
        "margin": "0.05",
    }


def test_legacy_journal_verified_cost_is_counted_before_any_new_reservation(tmp_path):
    journal = tmp_path / "legacy-cost.json"
    journal.write_text(json.dumps({
        "kind": "OPENROUTER_USD_ONE_RESERVATION_JOURNAL",
        "entries": [{
            "reservationId": "legacy-reservation",
            "reservedUsd": "0.10",
            "verifiedCostUsd": "0.90",
            "status": "returned",
        }],
    }), encoding="utf-8")
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
    with pytest.raises(ProviderFailure, match="openrouter_usd_budget_exhausted"):
        asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.06"))))
    snapshot = budget.snapshot()
    assert snapshot["callCount"] == 1
    assert snapshot["conservativeCommittedUsd"] == "0.90"
    assert snapshot["verifiedCostUsd"] == "0.90"


def test_verified_cost_above_reserve_is_committed_and_poisoned_over_cap_for_all_processes(tmp_path):
    journal = tmp_path / "verified-overrun.json"
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
    reservation = asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.20"))))
    asyncio.run(budget.mark(reservation, "returned", Decimal("0.99")))

    snapshot = budget.snapshot()
    assert snapshot["conservativeCommittedUsd"] == "0.99"
    assert snapshot["verifiedCostUsd"] == "0.99"
    assert snapshot["unknownCosts"] == {"count": 0, "conservativeReservedUsd": "0"}
    assert json.loads(journal.read_text(encoding="utf-8"))["metadata"]["overCap"] is True

    later = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
    with pytest.raises(ProviderFailure, match="openrouter_usd_budget_exhausted"):
        asyncio.run(later.reserve(**_reservation_kwargs(Decimal("0"))))


def test_unknown_remote_cost_remains_conservatively_reserved_in_snapshot(tmp_path):
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=tmp_path / "unknown.json")
    reservation = asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.23"))))
    asyncio.run(budget.mark(reservation, "cancelled_unknown_remote_cost"))
    snapshot = budget.snapshot()
    assert snapshot["conservativeCommittedUsd"] == "0.23"
    assert snapshot["verifiedCostUsd"] == "0"
    assert snapshot["unknownCosts"] == {"count": 1, "conservativeReservedUsd": "0.23"}
    assert snapshot["unknownRemoteEntries"] == [{
        "reservationId": reservation,
        "reservedUsd": "0.23",
        "status": "cancelled_unknown_remote_cost",
    }]


def test_corrupt_or_entries_missing_journal_fails_closed_without_reset(tmp_path):
    for name, text in (("corrupt.json", "{not-json"), ("missing-entries.json", json.dumps({"kind": "OPENROUTER_USD_ONE_RESERVATION_JOURNAL"}))):
        journal = tmp_path / name
        journal.write_text(text, encoding="utf-8")
        budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
        with pytest.raises(ProviderFailure, match="openrouter_budget_journal_invalid"):
            asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.01"))))
        assert journal.read_text(encoding="utf-8") == text


def test_exactly_empty_legacy_journal_initializes_but_whitespace_journal_is_invalid(tmp_path):
    empty = tmp_path / "legacy-empty.json"
    empty.write_text("", encoding="utf-8")
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=empty)
    asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.01"))))
    parsed = json.loads(empty.read_text(encoding="utf-8"))
    assert parsed["kind"] == "OPENROUTER_USD_ONE_RESERVATION_JOURNAL"
    assert len(parsed["entries"]) == 1

    whitespace = tmp_path / "corrupt-whitespace.json"
    whitespace.write_text(" \n", encoding="utf-8")
    with pytest.raises(ProviderFailure, match="openrouter_budget_journal_invalid"):
        asyncio.run(OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=whitespace).reserve(**_reservation_kwargs(Decimal("0.01"))))


def test_lock_timeout_is_bounded_and_fails_closed_without_skipping(tmp_path):
    """This is an actual inter-process lock contention test, not a mocked lock branch."""
    context = mp.get_context("spawn")
    journal = tmp_path / "locked.json"
    acquired = context.Event()
    release = context.Event()
    holder = context.Process(target=_spawn_lock_holder, args=(str(journal) + ".lock", acquired, release))
    holder.start()
    assert acquired.wait(10)
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
    started = time.monotonic()
    try:
        with pytest.raises(ProviderFailure, match="openrouter_budget_journal_lock_timeout"):
            asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.01"))))
    finally:
        release.set()
        holder.join(15)
    elapsed = time.monotonic() - started
    assert holder.exitcode == 0
    assert JOURNAL_LOCK_TIMEOUT_SECONDS - 0.75 <= elapsed <= JOURNAL_LOCK_TIMEOUT_SECONDS + 3
    with pytest.raises(ProviderFailure, match="openrouter_budget_journal_unavailable"):
        asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.01"))))


def test_non_finite_negative_and_boolean_amounts_are_rejected(tmp_path):
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=tmp_path / "numbers.json")
    for value in (True, Decimal("NaN"), Decimal("-0.01")):
        with pytest.raises(ValueError):
            asyncio.run(budget.reserve(**_reservation_kwargs(value)))
    reservation = asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.01"))))
    for value in (True, Decimal("NaN"), Decimal("-0.01")):
        with pytest.raises(ValueError):
            asyncio.run(budget.mark(reservation, "returned", value))


def test_mark_journal_failure_is_not_silent_and_current_instance_fails_closed(monkeypatch, tmp_path):
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=tmp_path / "mark-failure.json")
    reservation = asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.01"))))

    def fail_mark(*_args, **_kwargs):
        raise ProviderFailure("openrouter_budget_journal_unavailable")

    monkeypatch.setattr(budget, "_mark_persistently", fail_mark)
    with pytest.raises(ProviderFailure, match="openrouter_budget_journal_unavailable"):
        asyncio.run(budget.mark(reservation, "returned", Decimal("0.001")))
    with pytest.raises(ProviderFailure, match="openrouter_budget_journal_unavailable"):
        asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.01"))))


def test_snapshot_persists_tighter_ceiling_across_independent_instances(tmp_path):
    journal = tmp_path / "snapshot-ceiling.json"
    original = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
    asyncio.run(original.reserve(**_reservation_kwargs(Decimal("0.10"))))
    tighter = OpenRouterBudget(max_usd=Decimal("0.50"), journal_path=journal)
    assert tighter.snapshot()["currentCeilingUsd"] == "0.50"
    later = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=journal)
    with pytest.raises(ProviderFailure, match="openrouter_usd_budget_exhausted"):
        asyncio.run(later.reserve(**_reservation_kwargs(Decimal("0.41"))))
    assert later.snapshot()["currentCeilingUsd"] == "0.50"


def test_persistent_verified_cost_cannot_be_reduced_by_repeated_mark(tmp_path):
    budget = OpenRouterBudget(max_usd=Decimal("0.95"), journal_path=tmp_path / "monotonic.json")
    reservation = asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.10"))))
    asyncio.run(budget.mark(reservation, "returned", Decimal("0.30")))
    asyncio.run(budget.mark(reservation, "returned", Decimal("0.01")))
    assert budget.snapshot()["verifiedCostUsd"] == "0.30"
    assert budget.snapshot()["conservativeCommittedUsd"] == "0.30"


def test_memory_verified_cost_cannot_be_reduced_by_repeated_mark():
    budget = OpenRouterBudget(max_usd=Decimal("0.95"))
    reservation = asyncio.run(budget.reserve(**_reservation_kwargs(Decimal("0.10"))))
    asyncio.run(budget.mark(reservation, "returned", Decimal("0.30")))
    asyncio.run(budget.mark(reservation, "returned", Decimal("0.01")))
    assert budget.snapshot()["verifiedCostUsd"] == "0.30"
    assert budget.snapshot()["conservativeCommittedUsd"] == "0.30"
