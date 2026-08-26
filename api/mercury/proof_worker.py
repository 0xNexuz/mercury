from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import main
from .memory import IncidentMemoryStore
from .models import AnalyzeRequest, IncidentCreate, ResolveRequest, utc_now
from .proof import PROOF_CATEGORY, proof_store
from .provenance import commitments


def load_run(store: IncidentMemoryStore, run_id: str) -> dict[str, Any]:
    record = store.get_entity(PROOF_CATEGORY, run_id)
    if not record:
        raise RuntimeError("proof run not found")
    return record["body"]


def session_identity(label: str) -> dict[str, Any]:
    return {
        "session_id": f"SES-{label}-{uuid4().hex[:12].upper()}",
        "process_id": os.getpid(),
        "process_started_at": utc_now(),
        "runtime": f"python-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


def run_session_a(path: Path, run_id: str) -> dict[str, Any]:
    store = proof_store(path, run_id)
    main.store = store
    identity = session_identity("A")
    incident = main.create_incident(IncidentCreate(scenario_id="payments-queue"))
    baseline = main.analyze_incident(incident["incident_id"], AnalyzeRequest(memory_mode="forget"))
    resolved = main.resolve_incident(incident["incident_id"], ResolveRequest(
        executed_action="restart_worker", result="worse",
        detail="Restart causes duplicate queue processing", recovery_time_minutes=31,
        operator_feedback="modified", successful_action="drain_queue_then_rollback", supersedes=[],
    ))
    memory_record = store.incident_record(incident["incident_id"])
    if not memory_record or memory_record["body"].get("status") != "resolved":
        raise RuntimeError("Sibyl did not return the resolved Session A memory")
    journal_id = store.journal(
        evaluated=["hosted eligibility proof Session A persisted"],
        extra={"run_id": run_id, "session_id": identity["session_id"], "memory_id": memory_record["id"]},
    )
    proof = load_run(store, run_id)
    proof["status"] = "session_a_ended"
    proof["session_a"] = {
        **identity,
        "incident_id": incident["incident_id"],
        "baseline_decision": baseline["baseline_decision"],
        "recorded_outcome": resolved["outcome"],
        "incident_snapshot": resolved,
        "sibyl_memory_id": memory_record["id"],
        "sibyl_journal_id": journal_id,
        "write_confirmed": True,
        "read_after_write_confirmed": True,
        "process_ended": True,
        "process_ended_at": utc_now(),
    }
    proof["base"] = {
        **commitments(resolved),
        "status": "UNANCHORED",
        "network": "Base Sepolia",
        "chain_id": 84532,
        "transaction_hash": None,
    }
    store.set_entity(PROOF_CATEGORY, run_id, proof, status="active")
    return proof["session_a"]


def run_session_b(path: Path, run_id: str) -> dict[str, Any]:
    store = proof_store(path, run_id)
    main.store = store
    identity = session_identity("B")
    proof = load_run(store, run_id)
    session_a = proof.get("session_a") or {}
    if not session_a.get("process_ended"):
        raise RuntimeError("Session A termination is not confirmed")
    incident = main.create_incident(IncidentCreate(scenario_id="payments-queue"))
    counterfactual = main.analyze_incident(incident["incident_id"], AnalyzeRequest(memory_mode="forget"))
    informed = main.analyze_incident(incident["incident_id"], AnalyzeRequest(memory_mode="remember"))
    retrieved = informed["relevant_memories"]
    expected_memory = session_a.get("incident_id")
    if identity["process_id"] == session_a.get("process_id"):
        raise RuntimeError("Session B reused the Session A process")
    if informed["memory_status"] != "used" or expected_memory not in informed["memory_informed_decision"]["memory_evidence"]:
        raise RuntimeError("Session B did not retrieve Session A from Sibyl")
    if counterfactual["baseline_decision"]["action"] != "restart_worker" or informed["memory_informed_decision"]["action"] != "drain_queue_then_rollback":
        raise RuntimeError("retrieved memory did not produce the required deterministic decision change")
    journal_id = store.journal(
        evaluated=["hosted eligibility proof Session B retrieved Session A"],
        extra={"run_id": run_id, "session_id": identity["session_id"], "retrieved": expected_memory},
    )
    proof["status"] = "passed"
    proof["session_b"] = {
        **identity,
        "incident_id": incident["incident_id"],
        "sibyl_retrieval_event_id": journal_id,
        "retrieved_memory_id": session_a.get("sibyl_memory_id"),
        "retrieved_experience": retrieved[0],
        "counterfactual_decision": counterfactual["baseline_decision"],
        "memory_informed_decision": informed["memory_informed_decision"],
        "counterfactual_analysis": counterfactual,
        "memory_analysis": informed,
        "incident_snapshot": store.get(incident["incident_id"]),
        "policy": informed["policy"],
        "retrieval_terms": informed["retrieval_terms"],
        "memory_changed_decision": informed["memory_informed_decision"]["changed"],
        "process_ended": True,
        "process_ended_at": utc_now(),
    }
    store.set_entity(PROOF_CATEGORY, run_id, proof, status="active")
    return proof["session_b"]


def cli() -> None:
    if len(sys.argv) != 4 or sys.argv[1] not in {"session-a", "session-b"}:
        raise SystemExit("usage: python -m mercury.proof_worker session-a|session-b DB_PATH RUN_ID")
    phase, raw_path, run_id = sys.argv[1:]
    output = run_session_a(Path(raw_path), run_id) if phase == "session-a" else run_session_b(Path(raw_path), run_id)
    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    cli()
