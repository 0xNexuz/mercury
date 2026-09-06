# Architecture

```mermaid
flowchart LR
  Judge --> Vercel[Next.js on Vercel]
  Vercel --> API[Single FastAPI process]
  API --> Engine[Deterministic engine]
  API --> Sibyl[Sibyl SQLite/FTS5 on /data]
  Judge --> Wallet[Operator wallet]
  Wallet --> Base[IncidentReceipts on Base Sepolia]
  API --> BaseRPC[Receipt verifier]
```

Vercel is stateless and never stores incident memory. The single persistent VM owns the only cross-session database. Session workers are new Python processes and use isolated Sibyl tenants per proof run.

On-chain data contains only four commitments and the recorder address. Telemetry and mitigation outcomes remain simulated.
