# Sibyl memory and decision influence

MERCURY uses `sibyl-memory-client==0.4.9`, not a mock. Incident entities use category `incident` and name `INC-###`; the body contains the fingerprint, attempted and successful actions, operator lesson, recovery, confidence, reuse counters, supersession, trace, and receipt.

Candidate generation calls Sibyl `search_entities(..., category="incident", prefix=True)` for normalized fingerprint terms. Ranking is explainable:

| Feature | Weight |
|---|---:|
| Exact service | 0.35 |
| Symptom-token Jaccard | 0.30 |
| Exact category | 0.20 |
| Exact error signature | 0.10 |
| Exact dependency | 0.05 |

Resolved, non-superseded candidates require a score of at least `0.55`. Historical `worse` attempts penalize the same action; validated successful actions receive a stronger boost. A qualifying change raises decision confidence from `0.72` to `0.91` in the primary proof.

Verified memories start at `0.80`. Successful reuse adds `0.05` up to `0.98`; failed reuse subtracts `0.15` down to `0.10`. Operator-selected supersession sets `superseded_by` and removes the older lesson from influence.

FORGET never queries Sibyl and reports `memory_status=bypassed`. Search failures report `degraded`; they never claim memory was used.

