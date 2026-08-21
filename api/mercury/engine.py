from __future__ import annotations

import re
from typing import Any, Literal

from .models import AnalysisResponse, Decision, MemoryEvidence, MemoryMode, PolicyResult, ScoreBreakdown, utc_now
from .scenarios import ACTIONS

STOPWORDS = {"the", "a", "an", "and", "or", "is", "are", "to", "of", "after", "rapidly", "increasing", "rising"}
RELEVANCE_THRESHOLD = 0.55


def normalize(value: str | None) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (value or "").lower()))


def token_set(values: list[str]) -> set[str]:
    return {token for value in values for token in normalize(value).split() if token not in STOPWORDS}


def fingerprint(incident: dict[str, Any]) -> dict[str, Any]:
    return {
        "service": normalize(incident["service"]),
        "category": normalize(incident["category"]),
        "symptoms": sorted(token_set(incident["symptoms"])),
        "dependency": normalize(incident.get("dependency")) or None,
        "error_signature": normalize(incident.get("error_signature")) or None,
    }


def retrieval_terms(fp: dict[str, Any]) -> list[str]:
    values = [*fp["service"].split(), *fp["category"].split(), *fp["symptoms"]]
    values.extend((fp.get("dependency") or "").split())
    values.extend((fp.get("error_signature") or "").split())
    return list(dict.fromkeys(v for v in values if len(v) > 2))


def _exact(left: str | None, right: str | None) -> float:
    return 1.0 if left and right and left == right else 0.0


def score_memory(current: dict[str, Any], historical: dict[str, Any]) -> ScoreBreakdown:
    cfp = current["fingerprint"]
    hfp = historical["fingerprint"]
    cs, hs = set(cfp["symptoms"]), set(hfp["symptoms"])
    symptom_similarity = len(cs & hs) / len(cs | hs) if cs | hs else 0.0
    parts = {
        "service": 0.35 * _exact(cfp["service"], hfp["service"]),
        "symptoms": 0.30 * symptom_similarity,
        "category": 0.20 * _exact(cfp["category"], hfp["category"]),
        "error_signature": 0.10 * _exact(cfp.get("error_signature"), hfp.get("error_signature")),
        "dependency": 0.05 * _exact(cfp.get("dependency"), hfp.get("dependency")),
    }
    return ScoreBreakdown(**parts, total=round(sum(parts.values()), 4))


def policy_for(action: str) -> PolicyResult:
    risk = ACTIONS[action]["risk"]
    approval = risk in {"high_risk_change", "destructive"}
    return PolicyResult(
        action=action,
        risk_class=risk,
        approval_required=approval,
        autonomous_execution_allowed=risk == "safe_observation",
        reason=("Human approval is mandatory for high-risk or destructive actions." if approval else "Action remains within the configured reversible safety boundary."),
    )


def analyze(incident: dict[str, Any], candidates: list[dict[str, Any]], memory_mode: MemoryMode, degraded: bool = False) -> AnalysisResponse:
    trace: list[dict[str, Any]] = [{"at": utc_now(), "step": "incident_received", "incident_id": incident["incident_id"]}, {"at": utc_now(), "step": "fingerprint_created", "fingerprint": incident["fingerprint"]}]
    baseline = Decision(action=incident["baseline_action"], confidence=0.72)
    terms = retrieval_terms(incident["fingerprint"])
    evidence: list[MemoryEvidence] = []
    if memory_mode == "forget":
        trace.append({"at": utc_now(), "step": "memory_bypassed", "reason": "FORGET comparison requested"})
    else:
        trace.append({"at": utc_now(), "step": "memory_query", "terms": terms})
        for candidate in candidates:
            score = score_memory(incident, candidate)
            if score.total < RELEVANCE_THRESHOLD:
                continue
            evidence.append(MemoryEvidence(
                incident_id=candidate["incident_id"], score=score, confidence=float(candidate.get("confidence", 0.8)),
                attempted_actions=candidate.get("attempted_actions", []), successful_action=candidate.get("successful_action"),
                operator_lesson=candidate.get("operator_lesson"), created_at=candidate["created_at"],
            ))
        evidence.sort(key=lambda item: item.score.total * item.confidence, reverse=True)
        trace.append({"at": utc_now(), "step": "memories_retrieved", "count": len(evidence), "ids": [e.incident_id for e in evidence]})

    action_scores = {action: (1.0 if action == baseline.action else 0.35) for action in incident["candidate_actions"]}
    for item in evidence:
        source = next(c for c in candidates if c["incident_id"] == item.incident_id)
        influence = item.score.total * item.confidence
        for attempt in source.get("attempted_actions", []):
            if attempt["action"] in action_scores:
                action_scores[attempt["action"]] += {"worse": -1.25, "neutral": -0.25, "better": 0.65}[attempt["result"]] * influence
        successful = source.get("successful_action")
        if successful and successful.get("action") in action_scores:
            action_scores[successful["action"]] += 1.1 * influence

    selected = max(action_scores, key=lambda action: action_scores[action]) if evidence else baseline.action
    changed = selected != baseline.action
    informed_confidence = min(0.98, 0.72 + (0.19 if changed else 0.04 * len(evidence))) if evidence else 0.72
    informed = Decision(action=selected, confidence=round(informed_confidence, 2), changed=changed, memory_evidence=[item.incident_id for item in evidence])
    policy = policy_for(selected)
    trace.extend([{"at": utc_now(), "step": "baseline_decision", "decision": baseline.model_dump()}, {"at": utc_now(), "step": "memory_informed_decision", "decision": informed.model_dump(), "action_scores": action_scores}, {"at": utc_now(), "step": "policy_check", "policy": policy.model_dump()}])
    top = evidence[0] if evidence else None
    explanation = {
        "without_memory": f"The deterministic baseline recommends {ACTIONS[baseline.action]['label']} at {baseline.confidence:.0%} confidence.",
        "memory_retrieved": (f"{top.incident_id} matched at {top.score.total:.0%} and recorded a prior operational outcome." if top else "No qualifying historical incident was used."),
        "how_memory_changed": (f"Historical evidence penalized {ACTIONS[baseline.action]['label']} and selected {ACTIONS[selected]['label']}." if changed else "Memory did not produce enough evidence to change the baseline action."),
        "why_preferred": ("The selected action has stronger validated outcomes in contextually similar incidents." if changed else "The baseline remains the strongest supported action."),
    }
    status: Literal["used", "bypassed", "degraded", "no_match"] = "degraded" if degraded else "bypassed" if memory_mode == "forget" else "used" if evidence else "no_match"
    return AnalysisResponse(incident_id=incident["incident_id"], memory_mode=memory_mode, baseline_decision=baseline, memory_informed_decision=informed, policy=policy, relevant_memories=evidence, retrieval_terms=terms, memory_status=status, explanation=explanation, trace=trace)
