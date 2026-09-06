# Real vs simulated

| Capability | Status | Evidence / note |
|---|---|---|
| Sibyl entity persistence and FTS5 retrieval | REAL — LOCAL | official SDK and passing tests |
| Fresh-process A/B decision change | REAL — LOCAL | subprocess proof tests |
| Public persistent backend | BLOCKED | VM not yet created |
| Incident telemetry and actions | SIMULATED | UI and docs label this |
| Commitment hashing | REAL — LOCAL | deterministic tests |
| Base receipt verification logic | REAL — LOCAL | RPC fixture tests |
| Base Sepolia contract and receipt | BLOCKED | no verified address or transaction |
| Virtuals ACP | PLANNED | deferred |

The UI must continue to show UNANCHORED until the backend verifies a real transaction.
