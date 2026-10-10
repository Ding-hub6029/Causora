"""Local identity mismatch injection, not a real-model test."""
from dataclasses import replace
import pytest
from agent_day4.wire import PipelineError
from tests_day5.day5_fixtures import FixtureProvider, boardroom_request, execute, reviewed_run


@pytest.mark.parametrize(("field", "bad_value"), [("dataVersion", "other-version"), ("scenarioId", "nonexistent-scenario"), ("schemaVersion", "causora.contract.v999")])
def test_mismatched_request_identity_stops_all_model_stages(field, bad_value):
    run = reviewed_run()
    request = boardroom_request(run)
    request[field] = bad_value
    primary, critic = FixtureProvider(), FixtureProvider()
    with pytest.raises(PipelineError):
        execute(run, request=request, primary=primary, critic=critic)
    assert primary.events == critic.events == []


def test_run_simulation_request_correlation_mismatch_stops_all_stages():
    run = replace(reviewed_run(), simulation_request_id="not-the-simulation-envelope-request")
    primary, critic = FixtureProvider(), FixtureProvider()
    with pytest.raises(PipelineError):
        execute(run, primary=primary, critic=critic)
    assert primary.events == critic.events == []
