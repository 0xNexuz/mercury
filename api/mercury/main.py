from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .engine import analyze, fingerprint
from .memory import IncidentMemoryStore, MemoryUnavailable
from .models import AnalyzeRequest, IncidentCreate, ResolveRequest, VerifyReceiptRequest, utc_now
from .provenance import ReceiptVerificationError, commitments, verify_receipt
from .proof import create_run, execute_worker, get_run
from .scenarios import ACTIONS, SCENARIOS

app = FastAPI(title="MERCURY API", version="0.1.0", description="Persistent-memory incident intelligence powered by Sibyl Memory")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("WEB_ORIGIN", "http://localhost:3000"), "http://localhost:3001"], allow_methods=["*"], allow_headers=["*"])
store = IncidentMemoryStore()


def _require_incident(incident_id: str) -> dict[str, Any]:
    try:
        incident = store.get(incident_id)
    except MemoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident


@app.get("/api/health")
def health() -> dict[str, Any]:
    memory = store.health()
    return {"status": "ok" if memory["status"] == "online" else "degraded", "memory": memory, "base": {"network": "Base Sepolia", "chain_id": 84532, "contract_configured": bool(os.getenv("BASE_RECEIPTS_CONTRACT"))}, "virtuals": "deferred"}


@app.get("/api/scenarios")
def scenarios() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in SCENARIOS.values()]


@app.post("/api/proof-runs", status_code=status.HTTP_201_CREATED)
def create_proof_run() -> dict[str, Any]:
    try:
        return create_run(store.path)
    except MemoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/proof-runs/{run_id}")
def get_proof_run(run_id: str) -> dict[str, Any]:
    try:
        proof = get_run(store.path, run_id)
    except (ValueError, MemoryUnavailable) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not proof:
        raise HTTPException(status_code=404, detail="proof run not found")
    return proof


@app.post("/api/proof-runs/{run_id}/session-a")
def run_proof_session_a(run_id: str) -> dict[str, Any]:
    try:
        return execute_worker(store.path, run_id, "session-a")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RuntimeError, MemoryUnavailable) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/proof-runs/{run_id}/session-b")
def run_proof_session_b(run_id: str) -> dict[str, Any]:
    try:
        return execute_worker(store.path, run_id, "session-b")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RuntimeError, MemoryUnavailable) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/incidents", status_code=status.HTTP_201_CREATED)
def create_incident(request: IncidentCreate) -> dict[str, Any]:
    try:
        incident_id = store.next_incident_id()
    except MemoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if request.scenario_id:
        scenario = SCENARIOS.get(request.scenario_id)
        if not scenario:
            raise HTTPException(status_code=422, detail="unknown scenario_id")
        source = deepcopy(scenario)
    else:
        source = request.model_dump()
        source["id"] = None
        source["telemetry"] = []
    unknown = set(source["candidate_actions"]) - set(ACTIONS)
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown actions: {sorted(unknown)}")
    now = utc_now()
    incident = {
        "incident_id": incident_id, "scenario_id": source.get("id"), "title": source["title"], "service": source["service"],
        "category": source["category"], "symptoms": source["symptoms"], "dependency": source.get("dependency"),
        "error_signature": source.get("error_signature"), "deployment": source.get("deployment"), "candidate_actions": source["candidate_actions"],
        "baseline_action": source["baseline_action"], "preferred_action": source.get("preferred_action"), "telemetry": source.get("telemetry", []),
        "status": "open", "fingerprint": {}, "attempted_actions": [], "successful_action": None, "operator_lesson": None,
        "operator_feedback": None, "recovery_time_minutes": None, "confidence": 0.8, "created_at": now, "last_validated_at": None,
        "times_reused": 0, "reuse_successes": 0, "superseded_by": None, "last_analysis": None, "outcome": None, "base_receipt": None,
        "trace": [{"at": now, "step": "incident_created", "source": "simulator" if request.scenario_id else "manual"}],
    }
    incident["fingerprint"] = fingerprint(incident)
    try:
        store.save(incident)
        store.journal(evaluated=[f"{incident_id} created"], forward=["analyze incident"], extra={"incident_id": incident_id, "scenario_id": incident.get("scenario_id")})
    except MemoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return incident


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, Any]:
    return _require_incident(incident_id)


@app.post("/api/incidents/{incident_id}/analyze")
def analyze_incident(incident_id: str, request: AnalyzeRequest) -> dict[str, Any]:
    incident = _require_incident(incident_id)
    candidates: list[dict[str, Any]] = []
    degraded = False
    if request.memory_mode == "remember":
        try:
            from .engine import retrieval_terms
            candidates = store.search(retrieval_terms(incident["fingerprint"]), incident_id)
        except MemoryUnavailable:
            degraded = True
    result = analyze(incident, candidates, request.memory_mode, degraded)
    payload = result.model_dump()
    incident["last_analysis"] = payload
    incident["trace"] = [*incident.get("trace", []), *payload["trace"]]
    if not degraded:
        try:
            store.save(incident)
            store.journal(evaluated=[f"{incident_id} analyzed with memory={request.memory_mode}"], extra={"incident_id": incident_id, "memory_status": payload["memory_status"], "changed": payload["memory_informed_decision"]["changed"]})
        except MemoryUnavailable:
            payload["memory_status"] = "degraded"
    return payload


@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, request: ResolveRequest) -> dict[str, Any]:
    incident = _require_incident(incident_id)
    if incident["status"] == "resolved":
        raise HTTPException(status_code=409, detail="incident is already resolved")
    if request.executed_action not in incident["candidate_actions"]:
        raise HTTPException(status_code=422, detail="executed_action was not a candidate for this incident")
    if request.successful_action and request.successful_action not in incident["candidate_actions"]:
        raise HTTPException(status_code=422, detail="successful_action was not a candidate for this incident")
    if incident.get("scenario_id"):
        expected_result, expected_detail = SCENARIOS[incident["scenario_id"]]["outcomes"][request.executed_action]
        if request.result != expected_result or request.detail != expected_detail:
            raise HTTPException(status_code=422, detail="simulator outcomes are deterministic and cannot be overridden")
    for old_id in request.supersedes:
        old = _require_incident(old_id)
        if old["status"] != "resolved" or old_id == incident_id:
            raise HTTPException(status_code=422, detail=f"invalid supersession target: {old_id}")
    now = utc_now()
    incident["status"] = "resolved"
    incident["attempted_actions"].append({"action": request.executed_action, "result": request.result, "detail": request.detail})
    successful = request.successful_action or (request.executed_action if request.result == "better" else None)
    incident["successful_action"] = {"action": successful, "detail": request.detail} if successful else None
    incident["operator_lesson"] = request.detail
    incident["operator_feedback"] = request.operator_feedback
    incident["recovery_time_minutes"] = request.recovery_time_minutes
    incident["last_validated_at"] = now
    incident["outcome"] = {"executed_action": request.executed_action, "result": request.result, "detail": request.detail, "recovery_time_minutes": request.recovery_time_minutes, "operator_feedback": request.operator_feedback, "resolved_at": now}
    incident["trace"].append({"at": now, "step": "outcome_persisted", "outcome": incident["outcome"]})
    try:
        for old_id in request.supersedes:
            old = _require_incident(old_id)
            old["superseded_by"] = incident_id
            store.save(old)
        evidence_ids = ((incident.get("last_analysis") or {}).get("memory_informed_decision") or {}).get("memory_evidence", [])
        for evidence_id in evidence_ids:
            historical = store.get(evidence_id)
            if not historical or historical.get("superseded_by"):
                continue
            historical["times_reused"] = int(historical.get("times_reused", 0)) + 1
            if request.result == "better":
                historical["reuse_successes"] = int(historical.get("reuse_successes", 0)) + 1
                historical["confidence"] = min(0.98, float(historical.get("confidence", 0.8)) + 0.05)
            elif request.result == "worse":
                historical["confidence"] = max(0.10, float(historical.get("confidence", 0.8)) - 0.15)
            historical["last_validated_at"] = now
            store.save(historical)
        store.save(incident)
        store.journal(acted=[f"{incident_id}: {request.executed_action} -> {request.result}"], forward=["commit Base receipt"], extra={"incident_id": incident_id, "operator_feedback": request.operator_feedback})
    except MemoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return incident


@app.get("/api/incidents/{incident_id}/trace")
def get_trace(incident_id: str) -> dict[str, Any]:
    incident = _require_incident(incident_id)
    return {"incident_id": incident_id, "trace": incident.get("trace", [])}


@app.get("/api/incidents/{incident_id}/commitments")
def get_commitments(incident_id: str) -> dict[str, Any]:
    incident = _require_incident(incident_id)
    try:
        return {"incident_id": incident_id, **commitments(incident), "contract_address": os.getenv("BASE_RECEIPTS_CONTRACT"), "status": "READY_TO_ANCHOR"}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/incidents/{incident_id}/provenance/verify")
async def verify_provenance(incident_id: str, request: VerifyReceiptRequest) -> dict[str, Any]:
    incident = _require_incident(incident_id)
    try:
        receipt = await verify_receipt(request.transaction_hash, commitments(incident))
    except (ValueError, ReceiptVerificationError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    incident["base_receipt"] = receipt
    incident["trace"].append({"at": utc_now(), "step": "base_commitment_verified", "transaction_hash": request.transaction_hash})
    try:
        store.save(incident)
    except MemoryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return receipt
