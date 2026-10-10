"""Reproducibly export internal Day 2 models; no shared DTO is rewritten."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Day2Policy, DeterministicPreview


def main() -> None:
    folder = Path(__file__).parent / "schemas"
    folder.mkdir(exist_ok=True)
    for name, model in (("day2_test_policy.schema.json", Day2Policy),
                        ("day2_deterministic_preview.schema.json", DeterministicPreview)):
        dest = folder / name
        dest.write_text(json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(dest)


if __name__ == "__main__":
    main()
