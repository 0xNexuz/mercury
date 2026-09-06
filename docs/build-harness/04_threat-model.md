# Threat model

Assets are Sibyl history, proof integrity, operator wallet authority, RPC/contract configuration, and judge isolation.

| Threat | Defense | Status |
|---|---|---|
| Browser-state persistence fakes recall | No localStorage/cookies; refresh reads API/Sibyl | VERIFIED locally |
| Session process reuse | Distinct subprocess PID and UUID; exit code recorded | VERIFIED locally |
| Cross-judge leakage | Random run ID maps to dedicated Sibyl tenant | VERIFIED locally |
| Duplicate phase race | Per-run exclusive lock | VERIFIED locally |
| Memory failure presented as success | Failure closes proof and reports degraded state | VERIFIED locally |
| Wrong Base receipt | Verify chain, status, contract, event and commitments | VERIFIED with mocked RPC tests; TESTNET UNVERIFIED |
| Disk exhaustion/abuse | Single small judge deployment has no durable quota enforcement | P1 |
| Compromised frontend/API | Hosting and operator remain trusted | LIMITATION |

Private keys must never enter the repository, VM startup metadata, logs, or browser-visible configuration.
