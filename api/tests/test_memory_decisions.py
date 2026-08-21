from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mercury import main
from mercury.engine import policy_for
from mercury.memory import IncidentMemoryStore, MemoryUnavailable
from conftest import create, resolve


def seed_failed_restart(client: TestClient) -> dict:
    first = create(client)
    baseline = client.post(f"/api/incidents/{first['incident_id']}/analyze", json={"memory_mode": "forget"}).json()
    assert baseline["memory_informed_decision"]["action"] == "restart_worker"
    return resolve(client, first["incident_id"], "restart_worker", "worse", "Restart causes duplicate queue processing", "drain_queue_then_rollback")


def test_fresh_store_instance_retrieves_and_changes_decision(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = seed_failed_restart(client)
    assert first["incident_id"] == "INC-104"
    monkeypatch.setattr(main, "store", IncidentMemoryStore(tmp_path / "memory.db", "mercury-test"))
    second = create(client)
    result = client.post(f"/api/incidents/{second['incident_id']}/analyze", json={"memory_mode": "remember"}).json()
    assert result["memory_status"] == "used"
    assert result["baseline_decision"]["action"] == "restart_worker"
    assert result["memory_informed_decision"]["action"] == "drain_queue_then_rollback"
    assert result["memory_informed_decision"]["changed"] is True
    assert result["memory_informed_decision"]["memory_evidence"] == ["INC-104"]


def test_forget_bypasses_same_memory(client: TestClient) -> None:
    seed_failed_restart(client)
    second = create(client)
    result = client.post(f"/api/incidents/{second['incident_id']}/analyze", json={"memory_mode": "forget"}).json()
    assert result["memory_status"] == "bypassed"
    assert result["memory_informed_decision"]["action"] == "restart_worker"
    assert not result["relevant_memories"]


def test_irrelevant_memory_does_not_change_decision(client: TestClient) -> None:
    db = create(client, "database-saturation")
    client.post(f"/api/incidents/{db['incident_id']}/analyze", json={"memory_mode": "forget"})
    resolve(client, db["incident_id"], "restart_database", "worse", "Reconnect storm exhausts the pool again", "shed_load_and_raise_pool")
    payment = create(client)
    result = client.post(f"/api/incidents/{payment['incident_id']}/analyze", json={"memory_mode": "remember"}).json()
    assert result["memory_informed_decision"]["action"] == "restart_worker"
    assert result["memory_status"] == "no_match"


def test_successful_reuse_increases_confidence(client: TestClient) -> None:
    first = seed_failed_restart(client)
    second = create(client)
    analysis = client.post(f"/api/incidents/{second['incident_id']}/analyze", json={"memory_mode": "remember"}).json()
    assert analysis["memory_informed_decision"]["changed"]
    resolved = resolve(client, second["incident_id"], "drain_queue_then_rollback", "better", "Queue drains and deployment rollback restores stable processing")
    assert resolved["status"] == "resolved"
    historical = client.get(f"/api/incidents/{first['incident_id']}").json()
    assert historical["confidence"] == pytest.approx(0.85)
    assert historical["times_reused"] == 1
    assert historical["reuse_successes"] == 1


def test_failed_reuse_reduces_confidence(client: TestClient) -> None:
    first = seed_failed_restart(client)
    second = create(client)
    client.post(f"/api/incidents/{second['incident_id']}/analyze", json={"memory_mode": "remember"})
    resolve(client, second["incident_id"], "restart_worker", "worse", "Restart causes duplicate queue processing", "drain_queue_then_rollback")
    historical = client.get(f"/api/incidents/{first['incident_id']}").json()
    assert historical["confidence"] == pytest.approx(0.65)


def test_superseded_memory_is_excluded(client: TestClient) -> None:
    first = seed_failed_restart(client)
    replacement = create(client)
    response = client.post(f"/api/incidents/{replacement['incident_id']}/resolve", json={
        "executed_action": "drain_queue_then_rollback", "result": "better", "detail": "Queue drains and deployment rollback restores stable processing",
        "recovery_time_minutes": 12, "operator_feedback": "accepted", "successful_action": "drain_queue_then_rollback", "supersedes": [first["incident_id"]],
    })
    assert response.status_code == 200
    old = client.get(f"/api/incidents/{first['incident_id']}").json()
    assert old["superseded_by"] == replacement["incident_id"]
    current = create(client)
    result = client.post(f"/api/incidents/{current['incident_id']}/analyze", json={"memory_mode": "remember"}).json()
    assert first["incident_id"] not in result["memory_informed_decision"]["memory_evidence"]


def test_memory_cannot_bypass_safety_policy() -> None:
    policy = policy_for("drain_queue_then_rollback")
    assert policy.risk_class == "high_risk_change"
    assert policy.approval_required is True
    assert policy.autonomous_execution_allowed is False


def test_search_failure_reports_degraded_mode(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    incident = create(client)
    monkeypatch.setattr(main.store, "search", lambda *_: (_ for _ in ()).throw(MemoryUnavailable("offline")))
    result = client.post(f"/api/incidents/{incident['incident_id']}/analyze", json={"memory_mode": "remember"}).json()
    assert result["memory_status"] == "degraded"
    assert not result["relevant_memories"]

