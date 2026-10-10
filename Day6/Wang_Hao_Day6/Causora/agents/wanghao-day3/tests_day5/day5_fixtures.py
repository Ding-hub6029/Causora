"""TEST_FIXTURE_ONLY helpers for Day 5 reliability regressions.

These helpers construct local deterministic responses only.  They must never be
imported by production adapters and never read credentials or contact a provider.
"""
from __future__ import annotations

import asyncio
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = ROOT / "agents" / "wanghao-day3"
BACKEND = ROOT / "backend" / "backend"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from agent_day4.evidence import enrich_evidence
from agent_day4.inputs import VerifiedRun
from agent_day4.pipeline import run_boardroom
from agent_day4.wire import PipelineConfig

FIXTURE_MARKER = "TEST_FIXTURE_ONLY"


def reviewed_run() -> VerifiedRun:
    """Return a mutable candidate backed only by packaged TEST_FIXTURE_ONLY data."""
    fixture = json.loads((ROOT / "frontend/tests/fixtures/reviewed-v2-TEST_FIXTURE_ONLY.json").read_text(encoding="utf-8"))
    contract = json.loads((BACKEND / "reviewed/wang-2026-10-07/reviewed_contract.json").read_text(encoding="utf-8"))["contract"]
    evidence = json.loads((BACKEND / "demo_data/causora_day1_mock.json").read_text(encoding="utf-8"))["evidence"]
    renewal = next(item for item in evidence if item["id"] == "EV-019")
    evidence.append({
        **renewal,
        "id": "EV-020",
        "extractedField": "auto_renew",
        "extractedValue": True,
        "locatorBbox": None,
    })
    return VerifiedRun(
        copy.deepcopy(fixture["request"]),
        copy.deepcopy(fixture["response"]),
        copy.deepcopy(contract),
        tuple(enrich_evidence(evidence, source_root=BACKEND, contract=contract)),
        BACKEND,
        fixture["response"]["requestId"],
    )


def boardroom_request(run: VerifiedRun, scenario: str = "demand-drop") -> dict[str, str]:
    simulation = run.simulation_response["data"]["simulation"]
    return {
        "schemaVersion": "causora.contract.v1",
        "simulationId": simulation["simulationId"],
        "dataVersion": simulation["dataVersion"],
        "scenarioId": scenario,
    }


class FixtureProvider:
    """A deterministic in-memory provider recording every model payload."""

    kind = FIXTURE_MARKER
    model = "TEST_FIXTURE_ONLY-primary"
    family = "openai-gpt"

    def __init__(
        self,
        *,
        delay: float = 0.001,
        delays: dict[str, float] | None = None,
        failures: dict[str, Any] | None = None,
        mutations: dict[str, Any] | None = None,
        raw_outputs: dict[str, Any] | None = None,
    ) -> None:
        self.delay = delay
        self.delays = delays or {}
        self.failures = failures or {}
        self.mutations = mutations or {}
        self.raw_outputs = raw_outputs or {}
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.responses: list[dict[str, Any]] = []
        self.calls = 0

    async def complete(self, *, stage: str, payload: dict[str, Any], schema: dict[str, Any], system: str, **_kwargs: Any) -> Any:
        self.calls += 1
        self.events.append((stage, copy.deepcopy(payload)))
        await asyncio.sleep(self.delays.get(stage, self.delay))
        if stage in self.failures:
            error = self.failures[stage]
            if callable(error):
                error = error()
            self.responses.append({"stage": stage, "exception": type(error).__name__, "reason": getattr(error, "reason", str(error))})
            raise error
        if stage in self.raw_outputs:
            output = copy.deepcopy(self.raw_outputs[stage])
        else:
            output = self._valid_output(stage, payload)
            mutation = self.mutations.get(stage)
            if mutation:
                output = mutation(copy.deepcopy(output))
        self.responses.append({"stage": stage, "response": copy.deepcopy(output)})
        return output

    @staticmethod
    def _valid_output(stage: str, payload: dict[str, Any]) -> dict[str, Any]:
        if stage in ("CFO", "COO", "Risk"):
            return {
                "role": stage,
                "headline": "Review current tradeoffs",
                "body": "Review the referenced current-run metrics.",
                "status": "Watch",
                "metric_refs": payload["allowedMetricRefs"],
                "evidence_ids": payload["allowedEvidenceIds"][:1],
                "option_ids": payload["allowedOptionIds"],
                "claims": [],
            }
        if stage == "Critic":
            return {
                "cash_ceiling_enforced": True,
                "checked_roles": ["CFO", "COO", "Risk"],
                "coverage": [
                    "renewal_condition", "locked_forecast", "minimum_commitment", "demand_change",
                    "cash_pressure", "holding_cost", "omission", "conflict",
                ],
                "issues": [{
                    "kind": "compound_risk",
                    "severity": "High",
                    "headline": "Locked commitments interact with reduced demand",
                    "body": "The financial view omits the joint effect of fixed forecast commitments and reduced demand. Cash exposure must be assessed together with inventory carrying costs, without attributing every holding delta to the contract.",
                    "evidence_ids": ["EV-024", "EV-014"],
                    "claims": [],
                    "roles": ["CFO", "COO", "Risk"],
                }],
            }
        return {
            "option_id": payload["serverSelectedOptionId"],
            "option_action": payload["verifiedBusinessFacts"]["selectedAction"],
            "cash_ceiling_enforced": True,
            "recommendation": "Use the verified selected option for human review.",
            "rationale": "The selected alternative follows the existing cash ceiling checks and accounts for its sourcing action.",
            "metric_refs": ["delta_tco", "stockout_probability", "cash_outflow_p90"],
            "claims": [],
            "challenges": [],
        }


def execute(
    run: VerifiedRun | None = None,
    *,
    primary: FixtureProvider | None = None,
    critic: FixtureProvider | None = None,
    fallback: FixtureProvider | None = None,
    scenario: str = "demand-drop",
    request: dict[str, str] | None = None,
    config: PipelineConfig | None = None,
):
    """Run the formal pipeline against in-memory fixture responses only."""
    run = run or reviewed_run()
    primary = primary or FixtureProvider()
    critic = critic or FixtureProvider()
    critic.family = "google-gemini"
    critic.model = "TEST_FIXTURE_ONLY-gemini"
    return asyncio.run(run_boardroom(
        request or boardroom_request(run, scenario),
        run=run,
        provider=primary,
        critic_provider=critic,
        fallback_provider=fallback or primary,
        correlation_id="br-TEST_FIXTURE_ONLY-day5",
        config=config or PipelineConfig(total_timeout=4, stage_timeout=0.5, critic_timeout=0.5, retries=0, max_calls=8),
    ))


def recompute_selections(run: VerifiedRun) -> None:
    """Update only selection metadata after an explicit test constraint mutation."""
    request = run.simulation_request
    for scenario_id, rows in run.simulation_response["data"]["simulation"]["matrix"].items():
        violations: list[dict[str, str]] = []
        eligible: list[dict[str, Any]] = []
        for row in rows:
            codes: list[str] = []
            if row["feasible"] is not True:
                codes.append("infeasible")
            if row["stockoutProbability"] > request["riskThreshold"]:
                codes.append("stockout_threshold")
            if row["cashOutflowP90"] > request["budgetCeilingUsd"]:
                codes.append("cash_ceiling")
            violations.extend({"optionId": row["optionId"], "code": code} for code in codes)
            if not codes:
                eligible.append(row)
        winner = min(eligible, key=lambda row: (row["expectedTco"], row["optionId"]))["optionId"] if eligible else None
        run.simulation_response["data"]["selections"][scenario_id] = {
            "scenarioId": scenario_id,
            "status": "selected" if winner else "no_feasible_option",
            "recommendedOptionId": winner,
            "constraintViolations": violations,
        }
