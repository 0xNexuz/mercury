from __future__ import annotations

import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "api"))

from mercury.engine import analyze, fingerprint, retrieval_terms  # noqa: E402
from mercury.memory import IncidentMemoryStore  # noqa: E402
from mercury.models import utc_now  # noqa: E402
from mercury.scenarios import ACTIONS, SCENARIOS  # noqa: E402


CASES = [
    "payments-queue", "database-saturation", "api-latency", "expired-credential", "cache-stampede", "dependency-outage",
    "payments-queue", "database-saturation", "api-latency", "expired-credential", "cache-stampede", "dependency-outage",
    "payments-queue", "database-saturation", "api-latency", "expired-credential", "cache-stampede", "dependency-outage",
    "payments-queue", "dependency-outage",
]


def record(scenario_id: str, incident_id: str, resolved: bool) -> dict:
    scenario = deepcopy(SCENARIOS[scenario_id])
    item = {
        **scenario, "incident_id": incident_id, "scenario_id": scenario_id, "status": "resolved" if resolved else "open",
        "fingerprint": {}, "attempted_actions": [], "successful_action": None, "operator_lesson": None,
        "confidence": 0.8, "created_at": utc_now(), "last_validated_at": utc_now() if resolved else None,
        "times_reused": 0, "reuse_successes": 0, "superseded_by": None,
    }
    item["fingerprint"] = fingerprint(item)
    if resolved:
        failed = scenario["baseline_action"]
        preferred = scenario["preferred_action"]
        item["attempted_actions"] = [{"action": failed, "result": "worse", "detail": scenario["outcomes"][failed][1]}]
        item["successful_action"] = {"action": preferred, "detail": scenario["outcomes"][preferred][1]}
        item["operator_lesson"] = f"Avoid {failed}; {preferred} recovered this incident."
    return item


def aggregate(rows: list[dict], mode: str) -> dict:
    return {
        "cases": len(rows),
        "correct_mitigation_rate": round(mean(row[mode]["correct"] for row in rows), 3),
        "repeated_failure_rate": round(mean(row[mode]["repeated_failure"] for row in rows), 3),
        "unsafe_policy_violation_rate": round(mean(row[mode]["policy_violation"] for row in rows), 3),
        "mean_recovery_time_minutes": round(mean(row[mode]["recovery_minutes"] for row in rows), 2),
        "memory_use_rate": round(mean(row[mode]["memory_used"] for row in rows), 3),
        "decision_change_rate": round(mean(row[mode]["changed"] for row in rows), 3),
    }


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="mercury-mem-20-", ignore_cleanup_errors=True) as temp:
        store = IncidentMemoryStore(Path(temp) / "memory.db", "benchmark")
        for index, scenario_id in enumerate(SCENARIOS, 1):
            store.save(record(scenario_id, f"MEM-{index:03d}", True))
        rows = []
        for index, scenario_id in enumerate(CASES, 1):
            scenario = SCENARIOS[scenario_id]
            incident = record(scenario_id, f"CASE-{index:03d}", False)
            store.save(incident)
            candidates = store.search(retrieval_terms(incident["fingerprint"]), incident["incident_id"])
            without = analyze(incident, [], "forget")
            with_memory = analyze(incident, candidates, "remember")

            def measured(result: object) -> dict:
                response = result
                action = response.memory_informed_decision.action  # type: ignore[attr-defined]
                risk = ACTIONS[action]["risk"]
                approval = response.policy.approval_required  # type: ignore[attr-defined]
                return {
                    "action": action, "correct": int(action == scenario["preferred_action"]),
                    "repeated_failure": int(action == scenario["baseline_action"]),
                    "policy_violation": int(risk in {"high_risk_change", "destructive"} and not approval),
                    "recovery_minutes": scenario["recovery_minutes"][action],
                    "memory_used": int(response.memory_status == "used"),  # type: ignore[attr-defined]
                    "changed": int(response.memory_informed_decision.changed),  # type: ignore[attr-defined]
                }

            rows.append({"case_id": incident["incident_id"], "scenario": scenario_id, "without_memory": measured(without), "with_sibyl": measured(with_memory)})
        return {"benchmark": "MERCURY-MEM-20", "generated_at": utc_now(), "method": "20 deterministic incidents against six persisted historical lessons", "without_memory": aggregate(rows, "without_memory"), "with_sibyl": aggregate(rows, "with_sibyl"), "cases": rows}


if __name__ == "__main__":
    result = run()
    output_dir = ROOT / "evals" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "mercury-mem-20.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    no_mem, sibyl = result["without_memory"], result["with_sibyl"]
    markdown = f"""# MERCURY-MEM-20 measured results

Generated: {result['generated_at']}

| Metric | No-memory baseline | MERCURY + Sibyl |
|---|---:|---:|
| Correct mitigation rate | {no_mem['correct_mitigation_rate']:.0%} | {sibyl['correct_mitigation_rate']:.0%} |
| Repeated-failure rate | {no_mem['repeated_failure_rate']:.0%} | {sibyl['repeated_failure_rate']:.0%} |
| Unsafe policy-violation rate | {no_mem['unsafe_policy_violation_rate']:.0%} | {sibyl['unsafe_policy_violation_rate']:.0%} |
| Mean recovery time | {no_mem['mean_recovery_time_minutes']:.1f} min | {sibyl['mean_recovery_time_minutes']:.1f} min |
| Memory-use rate | {no_mem['memory_use_rate']:.0%} | {sibyl['memory_use_rate']:.0%} |
| Decision-change rate | {no_mem['decision_change_rate']:.0%} | {sibyl['decision_change_rate']:.0%} |

These are deterministic simulator measurements, not production claims. The JSON file contains every case.
"""
    (output_dir / "mercury-mem-20.md").write_text(markdown, encoding="utf-8")
    print(markdown)
