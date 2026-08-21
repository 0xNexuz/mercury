from __future__ import annotations

from typing import Any


ACTIONS: dict[str, dict[str, Any]] = {
    "observe_metrics": {"label": "Observe metrics", "risk": "safe_observation"},
    "restart_worker": {"label": "Restart worker", "risk": "reversible_mitigation"},
    "drain_queue_then_rollback": {"label": "Drain queue + rollback", "risk": "high_risk_change"},
    "restart_database": {"label": "Restart database", "risk": "high_risk_change"},
    "shed_load_and_raise_pool": {"label": "Shed load + raise pool", "risk": "high_risk_change"},
    "scale_out": {"label": "Scale out", "risk": "reversible_mitigation"},
    "rollback_deployment": {"label": "Rollback deployment", "risk": "high_risk_change"},
    "restart_service": {"label": "Restart service", "risk": "reversible_mitigation"},
    "rotate_credential": {"label": "Rotate credential", "risk": "high_risk_change"},
    "flush_cache": {"label": "Flush cache", "risk": "destructive"},
    "enable_request_coalescing": {"label": "Enable request coalescing", "risk": "reversible_mitigation"},
    "retry_aggressively": {"label": "Retry aggressively", "risk": "reversible_mitigation"},
    "open_circuit_breaker": {"label": "Open circuit breaker", "risk": "reversible_mitigation"},
}


SCENARIOS: dict[str, dict[str, Any]] = {
    "payments-queue": {
        "id": "payments-queue", "title": "Payments worker queue explosion", "service": "payments-worker",
        "category": "queue_saturation", "symptoms": ["queue depth rapidly increasing", "processing latency rising"],
        "dependency": "payments-queue", "error_signature": "duplicate-processing-risk", "deployment": "payments-worker@2026.08.20",
        "baseline_action": "restart_worker", "preferred_action": "drain_queue_then_rollback",
        "candidate_actions": ["restart_worker", "drain_queue_then_rollback", "observe_metrics"],
        "telemetry": [{"label": "Queue depth", "value": "18,240", "delta": "↑ 182%"}, {"label": "P95 latency", "value": "4.8s", "delta": "↑ 94%"}, {"label": "Error rate", "value": "21.4%", "delta": "↑ 21%"}],
        "outcomes": {"restart_worker": ["worse", "Restart causes duplicate queue processing"], "drain_queue_then_rollback": ["better", "Queue drains and deployment rollback restores stable processing"], "observe_metrics": ["worse", "Backlog continues to grow"]},
        "recovery_minutes": {"restart_worker": 48, "drain_queue_then_rollback": 17, "observe_metrics": 65},
    },
    "database-saturation": {
        "id": "database-saturation", "title": "Database connection saturation", "service": "orders-api", "category": "database_saturation",
        "symptoms": ["connection pool exhausted", "request timeouts increasing"], "dependency": "orders-postgres", "error_signature": "too-many-connections",
        "baseline_action": "restart_database", "preferred_action": "shed_load_and_raise_pool", "candidate_actions": ["restart_database", "shed_load_and_raise_pool", "observe_metrics"],
        "telemetry": [{"label": "Connections", "value": "498/500", "delta": "↑ 61%"}, {"label": "Timeouts", "value": "32%", "delta": "↑ 29%"}],
        "outcomes": {"restart_database": ["worse", "Reconnect storm exhausts the pool again"], "shed_load_and_raise_pool": ["better", "Load shedding restores headroom"], "observe_metrics": ["worse", "Timeouts spread upstream"]}, "recovery_minutes": {"restart_database": 55, "shed_load_and_raise_pool": 14, "observe_metrics": 70},
    },
    "api-latency": {
        "id": "api-latency", "title": "API latency after deployment", "service": "checkout-api", "category": "deployment_regression",
        "symptoms": ["latency increased after deployment", "error rate rising"], "dependency": "pricing-api", "error_signature": "release-regression",
        "baseline_action": "scale_out", "preferred_action": "rollback_deployment", "candidate_actions": ["scale_out", "rollback_deployment", "observe_metrics"],
        "telemetry": [{"label": "P95 latency", "value": "3.2s", "delta": "↑ 210%"}, {"label": "5xx", "value": "12.8%", "delta": "↑ 11%"}],
        "outcomes": {"scale_out": ["neutral", "Additional replicas reproduce the regression"], "rollback_deployment": ["better", "Previous build restores latency"], "observe_metrics": ["worse", "Customer impact grows"]}, "recovery_minutes": {"scale_out": 41, "rollback_deployment": 11, "observe_metrics": 58},
    },
    "expired-credential": {
        "id": "expired-credential", "title": "Expired service credential", "service": "billing-sync", "category": "credential_failure",
        "symptoms": ["authentication failures", "scheduled sync halted"], "dependency": "bank-gateway", "error_signature": "credential-expired",
        "baseline_action": "restart_service", "preferred_action": "rotate_credential", "candidate_actions": ["restart_service", "rotate_credential", "observe_metrics"],
        "telemetry": [{"label": "Auth failures", "value": "100%", "delta": "↑ 100%"}, {"label": "Sync lag", "value": "47m", "delta": "↑ 47m"}],
        "outcomes": {"restart_service": ["neutral", "Expired credential remains invalid"], "rotate_credential": ["better", "Authentication and sync recover"], "observe_metrics": ["worse", "Sync lag increases"]}, "recovery_minutes": {"restart_service": 37, "rotate_credential": 9, "observe_metrics": 80},
    },
    "cache-stampede": {
        "id": "cache-stampede", "title": "Cache stampede", "service": "catalog-api", "category": "cache_failure",
        "symptoms": ["cache miss rate spiking", "database load increasing"], "dependency": "catalog-redis", "error_signature": "cache-stampede",
        "baseline_action": "flush_cache", "preferred_action": "enable_request_coalescing", "candidate_actions": ["flush_cache", "enable_request_coalescing", "observe_metrics"],
        "telemetry": [{"label": "Cache misses", "value": "91%", "delta": "↑ 77%"}, {"label": "DB CPU", "value": "96%", "delta": "↑ 54%"}],
        "outcomes": {"flush_cache": ["worse", "Full invalidation amplifies the stampede"], "enable_request_coalescing": ["better", "Duplicate fills collapse and load falls"], "observe_metrics": ["worse", "Database saturates"]}, "recovery_minutes": {"flush_cache": 62, "enable_request_coalescing": 13, "observe_metrics": 76},
    },
    "dependency-outage": {
        "id": "dependency-outage", "title": "External dependency outage", "service": "shipping-api", "category": "dependency_outage",
        "symptoms": ["upstream requests timing out", "retry volume increasing"], "dependency": "carrier-api", "error_signature": "upstream-timeout",
        "baseline_action": "retry_aggressively", "preferred_action": "open_circuit_breaker", "candidate_actions": ["retry_aggressively", "open_circuit_breaker", "observe_metrics"],
        "telemetry": [{"label": "Upstream errors", "value": "88%", "delta": "↑ 84%"}, {"label": "Retry volume", "value": "8.4×", "delta": "↑ 740%"}],
        "outcomes": {"retry_aggressively": ["worse", "Retries amplify the dependency outage"], "open_circuit_breaker": ["better", "Fallback path contains the outage"], "observe_metrics": ["worse", "Thread pools exhaust"]}, "recovery_minutes": {"retry_aggressively": 59, "open_circuit_breaker": 12, "observe_metrics": 68},
    },
}
