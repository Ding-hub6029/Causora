"""TEST_FIXTURE_ONLY targeted evidence-support checks, not general entailment."""
import pytest
from agent_day4.wire import PipelineError
from tests_day5.day5_fixtures import FixtureProvider, execute


@pytest.mark.parametrize("stage", ["Risk", "Critic"])
@pytest.mark.parametrize("claim", [
    "The contract guarantees unlimited supply.",
    "The agreement assures uninterrupted deliveries.",
    "The supplier guarantees zero stockout risk.",
    "The contract permits waiving the exit fee.",
    "No termination fee applies to exiting supplier A.",
])
def test_valid_evidence_id_cannot_support_invented_supply_or_fee_guarantees(stage, claim):
    def mutate(value):
        if stage == "Critic":
            return {**value, "issues": [{**value["issues"][0], "body": claim, "evidence_ids": ["EV-024"]}]}
        return {**value, "body": claim, "evidence_ids": ["EV-024"]}
    primary = FixtureProvider(mutations={"Risk": mutate} if stage == "Risk" else {})
    critic = FixtureProvider(mutations={"Critic": mutate} if stage == "Critic" else {})
    # Both Critic transports must fail closed; a validated clean fallback would
    # correctly replace the rejected draft and is tested separately.
    fallback = FixtureProvider(mutations={"Critic": mutate})
    with pytest.raises(PipelineError):
        execute(primary=primary, critic=critic, fallback=fallback)


def test_unsupported_preferred_critic_can_only_return_clean_validated_fallback():
    unsupported = "The contract guarantees unlimited supply."
    critic = FixtureProvider(mutations={"Critic": lambda value: {**value, "issues": [{**value["issues"][0], "body": unsupported, "evidence_ids": ["EV-024"]}]}})
    result = execute(critic=critic)
    assert result.audit["fallbackReason"] == "evidence_claim_unsupported"
    assert all(unsupported not in item["body"] for item in result.envelope["data"]["criticIssues"])
