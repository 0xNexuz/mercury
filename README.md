# MERCURY

**Persistent-memory incident intelligence. MERCURY does not make the same operational mistake twice without evidence that circumstances changed.**

MERCURY is an incident-response command center built around the official [Sibyl Memory](https://github.com/Sibyl-Labs/Sibyl-Memory) Python SDK. It records incident outcomes in Sibyl's local-first SQLite/FTS5 memory, retrieves them from a completely fresh process, and deterministically changes the recommended response. A minimal Base Sepolia contract can anchor cryptographic commitments to the memory context, decision, and outcome without publishing incident details.

## Why memory is load-bearing

1. An incident occurs and its outcome is persisted through Sibyl.
2. The original process ends.
3. A fresh process starts with no React, process, localStorage, or secondary-database state.
4. MERCURY queries Sibyl and retrieves the prior incident.
5. The prior failed action is penalized and the validated mitigation is promoted.
6. Removing Sibyl changes the result back to the unsafe baseline.

The primary proof is `INC-104`: restarting `payments-worker` worsens the incident through duplicate queue processing. A later fresh session retrieves `INC-104`, changes `restart_worker` to `drain_queue_then_rollback`, and displays **MEMORY CHANGED THIS DECISION**.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. The named `mercury-sibyl` volume is the sole cross-session application store.

## Run natively

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r api\requirements-dev.txt
npm ci --legacy-peer-deps
$env:PYTHONPATH="api"
$env:SIBYL_DB_PATH="data\mercury-memory.db"
.\.venv\Scripts\python -m uvicorn mercury.main:app --port 8000
npm run dev
```

## Reproduce the eligibility proof

```powershell
.\.venv\Scripts\python scripts\fresh_session_smoke.py
```

The script launches two independent Python processes against the same Sibyl file and fails unless Session B cites `INC-104` and changes the action.

In the UI, choose **Record Session A**, then **Start Fresh Session B**. The FORGET side bypasses Sibyl; REMEMBER performs the real query.

## Verify

```powershell
.\.venv\Scripts\python -m pytest api\tests
.\.venv\Scripts\ruff check api evals scripts
npm run lint
npm test
npm run build
.\.venv\Scripts\python scripts\fresh_session_smoke.py
.\.venv\Scripts\python evals\run_benchmark.py
```

Contract tests run through the containerized Foundry profile:

```bash
docker compose --profile contracts run --rm contracts
```

## What is real

- **REAL:** Sibyl persistence, SQLite/FTS5 retrieval, fresh-process recall, deterministic memory influence, safety policy, commitment hashing, on-chain verification when configured.
- **SIMULATED:** incident telemetry, mitigations, and recovery outcomes.
- **OPTIONAL/DEFERRED:** Virtuals ACP specialist delegation.
- **HOSTED PREVIEW:** Vercel presents the visual client; the eligibility proof runs locally/Docker because Sibyl's durable file must live on a persistent volume.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Memory and influence](MEMORY.md)
- [Base receipts](BASE.md)
- [Demo script](DEMO.md)
- [Evaluation](EVALUATION.md)
- [Safety](SAFETY.md)

