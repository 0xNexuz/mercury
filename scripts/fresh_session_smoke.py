from __future__ import annotations

import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "api"))

from mercury.engine import analyze, fingerprint, retrieval_terms  # noqa: E402
from mercury.memory import IncidentMemoryStore  # noqa: E402
from mercury.models import utc_now  # noqa: E402
from mercury.scenarios import SCENARIOS  # noqa: E402


def incident(incident_id: str, resolved: bool) -> dict:
    scenario = deepcopy(SCENARIOS["payments-queue"])
    item = {**scenario, "incident_id": incident_id, "scenario_id": scenario["id"], "status": "resolved" if resolved else "open", "fingerprint": {}, "attempted_actions": [], "successful_action": None, "operator_lesson": None, "confidence": 0.8, "created_at": utc_now(), "last_validated_at": None, "times_reused": 0, "reuse_successes": 0, "superseded_by": None}
    item["fingerprint"] = fingerprint(item)
    if resolved:
        item["attempted_actions"] = [{"action": "restart_worker", "result": "worse", "detail": "Restart causes duplicate queue processing"}]
        item["successful_action"] = {"action": "drain_queue_then_rollback", "detail": "Operator drained the queue and rolled back"}
    return item


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "session-a":
        IncidentMemoryStore(sys.argv[2], "smoke").save(incident("INC-104", True))
        print("SESSION A: INC-104 persisted through Sibyl")
    elif len(sys.argv) == 3 and sys.argv[1] == "session-b":
        store = IncidentMemoryStore(sys.argv[2], "smoke")
        current = incident("INC-105", False)
        candidates = store.search(retrieval_terms(current["fingerprint"]), current["incident_id"])
        result = analyze(current, candidates, "remember")
        assert result.baseline_decision.action == "restart_worker"
        assert result.memory_informed_decision.action == "drain_queue_then_rollback"
        assert result.memory_informed_decision.changed
        assert result.memory_informed_decision.memory_evidence == ["INC-104"]
        print("SESSION B: MEMORY CHANGED THIS DECISION (INC-104 retrieved)")
    else:
        with tempfile.TemporaryDirectory(prefix="mercury-fresh-session-", ignore_cleanup_errors=True) as temp:
            db = str(Path(temp) / "memory.db")
            subprocess.run([sys.executable, __file__, "session-a", db], check=True)
            subprocess.run([sys.executable, __file__, "session-b", db], check=True)
            print("PASS: two independent Python processes produced different decisions because Sibyl persisted memory")

