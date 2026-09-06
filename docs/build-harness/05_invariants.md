# Invariants

| ID | Invariant | Enforcement | Evidence | Status |
|---|---|---|---|---|
| INV-001 | FORGET never queries Sibyl | Engine memory-mode branch | Python tests | VERIFIED |
| INV-002 | Memory influences only at score >= 0.55 | Explicit weighted scorer | Python tests | VERIFIED |
| INV-003 | Memory never lowers risk class | Action catalog then policy pass | Python tests | VERIFIED |
| INV-004 | Session B starts only after Session A exits | Orchestrator exit check | Hosted proof tests | VERIFIED |
| INV-005 | A/B use different processes | PID assertion | Hosted proof tests | VERIFIED |
| INV-006 | Proof refresh reloads from Sibyl | GET proof entity | Hosted proof tests | VERIFIED |
| INV-007 | VERIFIED Base means all commitments match | Backend receipt verifier | Provenance tests | VERIFIED locally |
| INV-008 | Hosted memory survives backend restart | Persistent /data disk | Public reboot test | UNVERIFIED |
