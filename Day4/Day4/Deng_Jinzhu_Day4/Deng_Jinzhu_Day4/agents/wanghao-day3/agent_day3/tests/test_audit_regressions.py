"""Compatibility filename with an independent Day 3 regression."""
from __future__ import annotations

import unittest

from agent_day3.adapter import Day3AgentDraft


class AdapterRegression(unittest.TestCase):
    def test_synthetic_draft_cannot_flip_decision_ready(self):
        with self.assertRaises(Exception):
            Day3AgentDraft.model_validate({
                "dataVersion": "x", "simulationId": "s", "scenarioId": "baseline",
                "sourceMode": "LOCAL_MOCK", "providerKind": "OFFLINE_STUB", "decisionReady": True,
                "agentOutputs": [],
            })


if __name__ == "__main__":
    unittest.main()
