"""Byte-stable JSON serialization shared by Windows and Unix workflows."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def json_utf8_lf_bytes(payload: Any, *, sort_keys: bool = False) -> bytes:
    """Return pretty JSON encoded as UTF-8 without BOM and exactly LF line endings."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=sort_keys, allow_nan=False)
    return (text + "\n").encode("utf-8")


def write_json_utf8_lf(path: Path, payload: Any, *, sort_keys: bool = False) -> None:
    """Write deterministic JSON bytes without Windows text-mode newline conversion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_utf8_lf_bytes(payload, sort_keys=sort_keys))
