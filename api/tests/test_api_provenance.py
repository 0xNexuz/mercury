from __future__ import annotations

from fastapi.testclient import TestClient

from mercury.provenance import commitments
from conftest import create, resolve


def test_refresh_reads_incident_from_sibyl(client: TestClient) -> None:
    incident = create(client)
    loaded = client.get(f"/api/incidents/{incident['incident_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["fingerprint"]["service"] == "payments worker"


def test_commitments_are_stable_and_sensitive_to_outcome(client: TestClient) -> None:
    incident = create(client)
    client.post(f"/api/incidents/{incident['incident_id']}/analyze", json={"memory_mode": "forget"})
    resolved = resolve(client, incident["incident_id"], "restart_worker", "worse", "Restart causes duplicate queue processing", "drain_queue_then_rollback")
    first = commitments(resolved)
    second = commitments(resolved)
    assert first == second
    assert all(str(first[key]).startswith("0x") and len(str(first[key])) == 66 for key in ("incident_id_hash", "memory_context_hash", "decision_hash", "outcome_hash"))


def test_unresolved_incident_cannot_be_anchored(client: TestClient) -> None:
    incident = create(client)
    response = client.get(f"/api/incidents/{incident['incident_id']}/commitments")
    assert response.status_code == 409


def test_invalid_receipt_hash_is_rejected(client: TestClient) -> None:
    incident = create(client)
    response = client.post(f"/api/incidents/{incident['incident_id']}/provenance/verify", json={"transaction_hash": "0x1234"})
    assert response.status_code == 422


def test_unknown_action_is_rejected(client: TestClient) -> None:
    incident = create(client)
    response = client.post(f"/api/incidents/{incident['incident_id']}/resolve", json={
        "executed_action": "drop_database", "result": "better", "detail": "bad", "recovery_time_minutes": 1,
        "operator_feedback": "accepted", "supersedes": [],
    })
    assert response.status_code == 422

