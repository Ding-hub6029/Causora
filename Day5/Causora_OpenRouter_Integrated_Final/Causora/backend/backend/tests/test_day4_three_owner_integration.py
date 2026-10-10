from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

import app.service as service
from app.boardroom_adapter import repository
from app.evidence_locator import pdfjs_user_space_bbox


ROOT = Path(__file__).resolve().parents[1]
REQUEST = json.loads((ROOT / "examples" / "simulate_request_v1.json").read_text(encoding="utf-8"))
PDF = ROOT / "public" / "demo" / "supplier_a_agreement.pdf"


@pytest.fixture(autouse=True)
def clear_repository() -> None:
    repository.clear()
    yield
    repository.clear()


def test_ev024_locator_uses_pdfjs_bottom_left_user_space(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression for the prior PyMuPDF-top-left/PDF.js-bottom-left mismatch."""
    monkeypatch.setenv("CAUSORA_DEV_UNREVIEWED_MODE", "UNREVIEWED_DEV_ONLY")
    client = TestClient(service.app)
    simulated = client.post("/api/simulate", json=REQUEST, headers={"X-Request-Id": "req-coordinate"})
    assert simulated.status_code == 200

    evidence = client.get("/api/evidence/EV-024", headers={"X-Request-Id": "req-ev024"})
    assert evidence.status_code == 200
    record = evidence.json()["data"]["evidence"]
    assert record["id"] == "EV-024"
    assert record["quoteMatched"] is True
    assert record["locatorBbox"] is not None

    with pymupdf.open(PDF) as document:
        page = document[record["page"] - 1]
        rectangles = page.search_for(record["quote"])
        assert rectangles
        x0 = min(rect.x0 for rect in rectangles)
        y0 = min(rect.y0 for rect in rectangles)
        x1 = max(rect.x1 for rect in rectangles)
        y1 = max(rect.y1 for rect in rectangles)
        height = page.mediabox.height
    expected = [round(float(x0), 4), round(float(height - y1), 4), round(float(x1), 4), round(float(height - y0), 4)]
    assert record["locatorBbox"] == expected
    assert pdfjs_user_space_bbox(PDF, record["page"], record["quote"]) == expected


def test_development_matrix_is_retained_for_evidence_but_cannot_start_formal_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAUSORA_DEV_UNREVIEWED_MODE", "UNREVIEWED_DEV_ONLY")
    client = TestClient(service.app)
    response = client.post("/api/simulate", json=REQUEST, headers={"X-Request-Id": "req-dev-retained"})
    assert response.status_code == 200
    body = response.json()
    simulation = body["data"]["simulation"]

    # The source-backed Evidence route remains available for trace inspection.
    evidence = client.get("/api/evidence/EV-024")
    assert evidence.status_code == 200
    assert evidence.json()["dataVersion"] == simulation["dataVersion"]

    # The same retained simulation cannot be promoted into the paid/formal path.
    boardroom = client.post("/api/boardroom", json={
        "schemaVersion": "causora.contract.v1",
        "simulationId": simulation["simulationId"],
        "dataVersion": simulation["dataVersion"],
        "scenarioId": "baseline",
    }, headers={"X-Request-Id": "req-dev-boardroom"})
    assert boardroom.status_code == 503
    assert boardroom.json()["error"]["details"]["reason"] == "review_pending"
    assert boardroom.headers["x-causora-current-simulation"] == simulation["simulationId"]


def test_invalid_locator_source_is_rejected_not_served(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAUSORA_DEV_UNREVIEWED_MODE", "UNREVIEWED_DEV_ONLY")
    client = TestClient(service.app)
    good = client.post("/api/simulate", json=REQUEST)
    assert good.status_code == 200
    record = repository.current()
    # A physical source change invalidates Evidence/Boardroom access on the next
    # request rather than showing a stale highlight.  Patch the source resolver
    # without changing packaged evidence bytes.
    monkeypatch.setattr("app.boardroom_adapter._resolve_source", lambda *_args: Path("/missing/source.pdf"))
    broken = client.get("/api/evidence/EV-024")
    assert broken.status_code == 503
    assert broken.json()["error"]["details"]["reason"] == "evidence_source_invalid"
    assert record.simulation_id == good.json()["data"]["simulation"]["simulationId"]
