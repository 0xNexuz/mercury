from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


OutcomeResult = Literal["better", "neutral", "worse"]
MemoryMode = Literal["forget", "remember"]
RiskClass = Literal["safe_observation", "reversible_mitigation", "high_risk_change", "destructive"]


class Fingerprint(BaseModel):
    service: str
    category: str
    symptoms: list[str]
    dependency: str | None = None
    error_signature: str | None = None


class IncidentCreate(BaseModel):
    scenario_id: str | None = None
    service: str | None = None
    title: str | None = None
    category: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    dependency: str | None = None
    error_signature: str | None = None
    deployment: str | None = None
    candidate_actions: list[str] = Field(default_factory=list)
    baseline_action: str | None = None

    @model_validator(mode="after")
    def scenario_or_manual(self) -> "IncidentCreate":
        if self.scenario_id:
            return self
        if not all((self.service, self.title, self.category, self.symptoms, self.baseline_action)):
            raise ValueError("manual incidents require service, title, category, symptoms, and baseline_action")
        if self.baseline_action not in self.candidate_actions:
            raise ValueError("baseline_action must be included in candidate_actions")
        return self


class AnalyzeRequest(BaseModel):
    memory_mode: MemoryMode


class ResolveRequest(BaseModel):
    executed_action: str
    result: OutcomeResult
    detail: str = Field(min_length=1, max_length=1000)
    recovery_time_minutes: int = Field(ge=0, le=10080)
    operator_feedback: Literal["accepted", "rejected", "modified", "rolled_back", "escalated"]
    successful_action: str | None = None
    supersedes: list[str] = Field(default_factory=list)


class VerifyReceiptRequest(BaseModel):
    transaction_hash: str = Field(pattern=r"^0x[a-fA-F0-9]{64}$")


class Decision(BaseModel):
    action: str
    confidence: float = Field(ge=0, le=1)
    changed: bool = False
    memory_evidence: list[str] = Field(default_factory=list)


class PolicyResult(BaseModel):
    action: str
    risk_class: RiskClass
    approval_required: bool
    autonomous_execution_allowed: bool
    reason: str


class ScoreBreakdown(BaseModel):
    service: float
    symptoms: float
    category: float
    error_signature: float
    dependency: float
    total: float


class MemoryEvidence(BaseModel):
    incident_id: str
    score: ScoreBreakdown
    confidence: float
    attempted_actions: list[dict[str, Any]]
    successful_action: dict[str, Any] | None = None
    operator_lesson: str | None = None
    created_at: str


class AnalysisResponse(BaseModel):
    incident_id: str
    memory_mode: MemoryMode
    baseline_decision: Decision
    memory_informed_decision: Decision
    policy: PolicyResult
    relevant_memories: list[MemoryEvidence]
    retrieval_terms: list[str]
    memory_status: Literal["used", "bypassed", "degraded", "no_match"]
    explanation: dict[str, str]
    trace: list[dict[str, Any]]

