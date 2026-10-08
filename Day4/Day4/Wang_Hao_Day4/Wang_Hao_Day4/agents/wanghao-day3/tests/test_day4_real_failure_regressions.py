"""Local regressions from a rejected OpenRouter response; never new network proof."""
import asyncio
import copy
import json

import pytest

from day4_fixtures import FixtureProvider, reviewed_run, boardroom_request
from agent_day4.pipeline import _scan_fields, run_boardroom
from agent_day4.provider import ProviderFailure
from agent_day4.wire import PipelineConfig, PipelineError


def test_grammatical_options_phrase_does_not_hide_business_numbers():
    body = "Cash planning is framed around renewal and holding impacts for one set of options."
    _scan_fields({"body": body}, ["body"], [], {}, [], [])
    for bad in (body + " Cost is one dollar.", body + " Risk is 20%.", "Use one supplier.", "Pay one fixed fee."):
        with pytest.raises(PipelineError) as caught:
            _scan_fields({"body": bad}, ["body"], [], {}, [], [])
        assert caught.value.reason == "numeric_guardrail_rejected"


def test_bad_gemini_then_numeric_rejected_gpt_publishes_no_brief_or_synthesis():
    class RecordingPrimary(FixtureProvider):
        def __init__(self):
            super().__init__()
            self.seen_stages = []

        async def complete(self, **kwargs):
            self.seen_stages.append(kwargs["stage"])
            return await super().complete(**kwargs)

    class BadGemini(FixtureProvider):
        family = "google-gemini"

        async def complete(self, **kwargs):
            raise ProviderFailure("provider_bad_request")

    class NumericBadFallback(FixtureProvider):
        async def complete(self, **kwargs):
            value = await super().complete(**kwargs)
            value["issues"][0]["body"] = "Cash planning requires one dollar."
            return value

    run = reviewed_run()
    snapshot = json.dumps({"request": run.simulation_request, "response": run.simulation_response},
                          sort_keys=True, default=str)
    primary = RecordingPrimary()
    gemini = BadGemini()
    gemini.family = "google-gemini"
    fallback = NumericBadFallback()
    with pytest.raises(PipelineError) as caught:
        asyncio.run(run_boardroom(
            boardroom_request(run), run=run, provider=primary, critic_provider=gemini,
            fallback_provider=fallback, correlation_id="br-LOCAL_REJECTED_CRITIC_ONLY",
            config=PipelineConfig(total_timeout=5, stage_timeout=1, critic_timeout=1,
                                  retries=0, max_calls=6)))
    assert caught.value.reason == "critic_unavailable"
    assert "Synthesizer" not in primary.seen_stages
    assert set(primary.seen_stages) == {"CFO", "COO", "Risk"}
    assert json.dumps({"request": run.simulation_request, "response": run.simulation_response},
                      sort_keys=True, default=str) == snapshot
