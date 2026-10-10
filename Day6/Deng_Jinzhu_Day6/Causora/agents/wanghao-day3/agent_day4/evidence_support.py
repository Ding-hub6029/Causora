"""Targeted unsupported-claim policy for the current vetted synthetic contract.

An existing citation ID is not proof of arbitrary natural-language entailment.
This deterministic guard covers specific unsupported supply guarantees and fee
waivers. It is intentionally NOT a general semantic entailment scorer.
"""
from __future__ import annotations
import re
from .wire import PipelineError

_PATTERNS = (
    re.compile(r"\b(?:guarantee\w*|assur\w*|ensure\w*|promise\w*)\b.{0,80}\b(?:unlimited|uninterrupted|unrestricted|continuous|risk[- ]free)\b.{0,35}\b(?:suppl\w*|deliver\w*|availability)\b", re.I),
    re.compile(r"\b(?:unlimited|uninterrupted|unrestricted|risk[- ]free)\b.{0,35}\b(?:suppl\w*|deliver\w*)\b.{0,50}\b(?:guarantee\w*|assur\w*|promise\w*)\b", re.I),
    re.compile(r"\b(?:guarantee\w*|assur\w*|ensure\w*)\b.{0,60}\b(?:zero|no)\b.{0,30}\b(?:stockout|shortage|delivery risk)\b", re.I),
    re.compile(r"\b(?:waiv\w*|exempt\w*|forgiv\w*|eliminat\w*)\b.{0,45}\b(?:exit|termination)\b.{0,15}\b(?:fee|cost|charge)\b", re.I),
    re.compile(r"\b(?:exit|termination)\b.{0,15}\b(?:fee|cost|charge)\b.{0,40}\b(?:waiv\w*|exempt\w*|forgiv\w*)\b", re.I),
    re.compile(r"\bno\s+(?:exit|termination)\s+(?:fee|cost|charge)\b.{0,60}\b(?:exit\w*|terminat\w*)\b", re.I),
)


def check_evidence_prose(text: str, *, stage: str) -> None:
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for pattern in _PATTERNS:
            found = pattern.search(sentence)
            if not found:
                continue
            prefix = sentence[max(0, found.start() - 50):found.start()]
            matched = found.group()
            # A statement explaining that there is no guarantee is allowed. Do
            # not confuse a general 'no termination fee' with a guarantee denial.
            denial = re.search(r"\b(?:does not|do not|cannot|never|must not)\s*(?:explicitly\s*)?$", prefix, re.I)
            denial = denial or re.search(r"\b(?:does not|do not|cannot|never)\b.{0,12}\b(?:guarantee|assure|promise)\b", matched, re.I)
            if denial:
                continue
            raise PipelineError("evidence_claim_unsupported", status=422,
                                details={"stage": stage, "violations": ["unsupported_supply_guarantee_or_fee_waiver"],
                                         "policy": "targeted-vetted-contract-v1-not-general-entailment"})
