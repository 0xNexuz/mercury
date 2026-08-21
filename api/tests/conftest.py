from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))

from mercury import main  # noqa: E402
from mercury.memory import IncidentMemoryStore  # noqa: E402


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "store", IncidentMemoryStore(tmp_path / "memory.db", "mercury-test"))
    return TestClient(main.app)


def create(client: TestClient, scenario_id: str = "payments-queue") -> dict:
    response = client.post("/api/incidents", json={"scenario_id": scenario_id})
    assert response.status_code == 201, response.text
    return response.json()


def resolve(client: TestClient, incident_id: str, action: str, result: str, detail: str, successful: str | None = None) -> dict:
    response = client.post(f"/api/incidents/{incident_id}/resolve", json={
        "executed_action": action, "result": result, "detail": detail, "recovery_time_minutes": 20,
        "operator_feedback": "modified", "successful_action": successful, "supersedes": [],
    })
    assert response.status_code == 200, response.text
    return response.json()

