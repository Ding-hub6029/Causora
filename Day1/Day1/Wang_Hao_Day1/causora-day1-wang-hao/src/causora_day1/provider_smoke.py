"""Minimal plain/JSON-schema connectivity probe; credentials are never printed or saved."""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from openai import OpenAI

SCHEMA = {"name": "connectivity_probe", "strict": True, "schema": {
    "type": "object", "properties": {"ready": {"type": "boolean"}},
    "required": ["ready"], "additionalProperties": False}}


def valid_structured_reply(text: str) -> bool:
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return False
    # In Python, True == 1 == 1.0: equality alone is NOT JSON-schema validation.
    return type(parsed) is dict and set(parsed) == {"ready"} and type(parsed["ready"]) is bool and parsed["ready"] is True


def _check(client: OpenAI, model: str, structured: bool) -> dict:
    started = time.monotonic()
    mode = "strict_json_schema" if structured else "plain_text"
    try:
        kwargs = {"model": model, "messages": [{"role": "user", "content":
            "Connectivity check. Return JSON with ready true." if structured else
            "Connectivity check. Answer with the single word READY."}],
            "max_completion_tokens": 768}
        if structured:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": SCHEMA}
        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        text = choice.message.content or ""
        ok = valid_structured_reply(text) if structured else text.strip().strip('.!"').upper() == "READY"
        return {"mode": mode, "ok": bool(ok and choice.finish_reason == "stop"),
                "nonempty_response": bool(text.strip()), "finish_reason": choice.finish_reason,
                "latency_seconds": round(time.monotonic() - started, 2)}
    except Exception as exc:
        return {"mode": mode, "ok": False,
                "latency_seconds": round(time.monotonic() - started, 2),
                "error_type": type(exc).__name__}


def run(models: list[str], *, environ: Mapping[str, str] | None = None,
        client_factory: Callable | None = None) -> dict:
    env = os.environ if environ is None else environ
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "transport": "configured OpenAI-compatible endpoint; not proof of direct-vendor credentials",
              "results": []}
    if not env.get("OPENAI_API_KEY") or not env.get("OPENAI_API_BASE"):
        report["results"] = [{"model": model, "checks": [{"mode": "environment", "ok": False,
            "error_type": "MissingEnvironment"}]} for model in models]
        return report
    factory = client_factory or OpenAI
    try:
        client = factory(api_key=env["OPENAI_API_KEY"], base_url=env["OPENAI_API_BASE"],
                         timeout=45, max_retries=0)
    except Exception as exc:
        report["results"] = [{"model": model, "checks": [{"mode": "client_init", "ok": False,
            "error_type": type(exc).__name__}]} for model in models]
        return report
    for model in models:
        report["results"].append({"model": model, "checks": [
            _check(client, model, structured=False), _check(client, model, structured=True)]})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["gpt-5-nano", "gemini-3-flash-preview"])
    parser.add_argument("--output", type=Path, default=Path("reports/provider_smoke_current.json"))
    args = parser.parse_args()
    report = run(args.models)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if all(check["ok"] for result in report["results"] for check in result["checks"]) else 1)
