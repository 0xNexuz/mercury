from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient


def create_proof(client: TestClient) -> dict:
    response = client.post("/api/proof-runs")
    assert response.status_code == 201, response.text
    return response.json()


def test_real_cross_process_sibyl_proof_and_refresh(client: TestClient) -> None:
    proof = create_proof(client)
    run_id = proof["run_id"]
    assert client.post(f"/api/proof-runs/{run_id}/session-b").status_code == 409
    after_a = client.post(f"/api/proof-runs/{run_id}/session-a")
    assert after_a.status_code == 200, after_a.text
    session_a = after_a.json()["session_a"]
    assert session_a["write_confirmed"] and session_a["read_after_write_confirmed"]
    assert session_a["process_ended"] and session_a["orchestrator_confirmed_exit_code"] == 0
    after_b = client.post(f"/api/proof-runs/{run_id}/session-b")
    assert after_b.status_code == 200, after_b.text
    complete = after_b.json()
    session_b = complete["session_b"]
    assert complete["status"] == "passed"
    assert session_a["process_id"] != session_b["process_id"]
    assert session_b["retrieved_memory_id"] == session_a["sibyl_memory_id"]
    assert session_b["counterfactual_decision"]["action"] == "restart_worker"
    assert session_b["memory_informed_decision"]["action"] == "drain_queue_then_rollback"
    assert session_b["memory_changed_decision"] is True
    assert client.get(f"/api/proof-runs/{run_id}").json() == complete


def test_proof_runs_are_tenant_isolated_for_multiple_judges(client: TestClient) -> None:
    first, second = create_proof(client), create_proof(client)
    def run_a(run_id: str) -> dict:
        response = client.post(f"/api/proof-runs/{run_id}/session-a")
        assert response.status_code == 200, response.text
        return response.json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(pool.map(run_a, [first["run_id"], second["run_id"]]))
    assert a["session_a"]["incident_id"] == b["session_a"]["incident_id"] == "INC-104"
    assert a["session_a"]["sibyl_memory_id"] != b["session_a"]["sibyl_memory_id"]
    assert client.get(f"/api/proof-runs/{first['run_id']}").json()["session_a"]["sibyl_memory_id"] == a["session_a"]["sibyl_memory_id"]
    assert client.get(f"/api/proof-runs/{second['run_id']}").json()["session_a"]["sibyl_memory_id"] == b["session_a"]["sibyl_memory_id"]


def test_duplicate_session_execution_is_rejected(client: TestClient) -> None:
    run_id = create_proof(client)["run_id"]
    assert client.post(f"/api/proof-runs/{run_id}/session-a").status_code == 200
    assert client.post(f"/api/proof-runs/{run_id}/session-a").status_code == 409
