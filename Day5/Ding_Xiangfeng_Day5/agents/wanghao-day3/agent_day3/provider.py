"""Server-side OpenAI-compatible proxy; no key or provider code goes to frontend."""
from __future__ import annotations

import json
import os
from typing import Any

from .models import Role


class SandboxProxyProvider:
    """Opt-in model provider. Uses OPENAI_API_KEY/OPENAI_API_BASE from environment.

    Default model was present in the live catalog on 2026-10-06; recheck the
    catalog before switching model IDs. This is for server-side use only.
    """
    kind = "MODEL_PROXY"

    def __init__(self, model: str = "gpt-5-mini"):
        if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_API_BASE"):
            raise RuntimeError("Model proxy is not configured in this server environment")
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"],
                                  base_url=os.environ["OPENAI_API_BASE"], timeout=20.0, max_retries=0)
        self.model = model

    async def complete(self, *, role: Role, system: str,
                       payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": "Analyse this typed role view and respect its explicit sourceMode and provenance. Reply in JSON only.\n" +
                           json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)}],
            response_format={"type": "json_schema", "json_schema": {
                "name": f"causora_{role.lower()}_analysis", "strict": True, "schema": schema}},
            max_completion_tokens=2500,
            extra_body={"reasoning": {"effort": "minimal"}},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty provider response")
        value = json.loads(content)
        if not isinstance(value, dict):
            raise ValueError("Provider response must be a JSON object")
        return value


class OfflineStubProvider:
    """A deterministic TEST DOUBLE; never label its sentences as AI output."""
    kind = "OFFLINE_STUB"

    async def complete(self, *, role: Role, system: str,
                       payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        refs = payload["allowedMetricRefs"]
        evidence = payload["allowedEvidenceIds"]
        return {"role": role,
                "headline": {"CFO": "Financial tradeoffs need review",
                             "COO": "Service continuity needs review",
                             "Risk": "Contract exposure needs review"}[role],
                "reason_text": "This synthetic illustration points to a tradeoff; inspect the referenced fields before deciding.",
                "option_ids": ["D0", "D1", "D2"],
                "metric_refs": refs[:2],
                "evidence_ids": evidence[:1] if role == "Risk" else [],
                "status": "Watch"}
