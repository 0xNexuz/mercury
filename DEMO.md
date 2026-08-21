# Demo

1. Start MERCURY with Docker Compose or both native services.
2. Click **1 · Record Session A**.
3. Show `INC-104`: baseline restart, simulated duplicate processing, operator recovery by draining and rolling back.
4. Stop/restart the API if desired; the Sibyl volume/file remains.
5. Click **2 · Start Fresh Session B**.
6. Show FORGET: `restart_worker`, 72% confidence, no memory query.
7. Show REMEMBER: Sibyl ID `INC-104`, relevance breakdown, prior failed restart, `drain_queue_then_rollback`, 91% confidence.
8. Expand Technical Evidence and walk through query, scores, trace, and safety gate.
9. Approve the simulated response; explain that no production action runs.
10. If the Base contract is configured, connect an operator wallet, anchor, and show the verified transaction. Otherwise show `NOT ANCHORED`.

CLI proof: `python scripts/fresh_session_smoke.py`.

