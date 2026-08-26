# Architecture

```text
Incident → fingerprint → Sibyl FTS5 retrieval → relevance scoring
         → baseline decision → memory influence → safety policy
         → operator approval → simulated outcome → Sibyl update
         → canonical hashes → Base Sepolia receipt verification
```

The Next.js client calls a stateless FastAPI service. The service opens the official `MemoryClient.local(...)` against one configured Sibyl database. Open incidents, resolved incidents, traces, operator feedback, reuse quality, and verified receipt metadata all live as Sibyl entities/journal events. There is no second application database.

The public eligibility proof is orchestrated by `proof.py` and `proof_worker.py`. A random proof-run ID maps to a dedicated Sibyl tenant. Session A writes a resolved incident and exits; only after its subprocess exit is confirmed may a distinct Session B process query the same Sibyl file. The inspector reloads from Sibyl using the URL locator. Browser storage is never part of the proof.

The deterministic engine is intentionally outside model reasoning. Every response exposes the baseline, the memory-informed result, evidence IDs, feature scores, action-score changes, and policy outcome.

Core modules are `api/mercury/memory.py`, `engine.py`, `provenance.py`, and `main.py`. The Solidity receipt contract is isolated under `contracts/`. Virtuals can later implement a specialist provider behind a low-confidence branch without becoming a prerequisite for Sibyl.
