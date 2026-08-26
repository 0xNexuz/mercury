# Demo

[Watch the 27-second captions-only product demo](./public/mercury-demo.mp4). It is generated reproducibly with `python scripts/render_demo_video.py`.

1. Start MERCURY with Docker Compose or both native services.
2. Click **1 · Run Session A**.
3. Show `INC-104`: baseline restart, simulated duplicate processing, confirmed Sibyl write, and terminated worker process.
4. Stop/restart the API if desired; the Sibyl volume/file and proof record remain.
5. Click **2 · Start Fresh Session B**, then **View Proof**.
6. Show FORGET: `restart_worker`, 72% confidence, no memory query.
7. Show REMEMBER: Sibyl ID `INC-104`, relevance breakdown, prior failed restart, `drain_queue_then_rollback`, 91% confidence.
8. In View Proof, compare Session A/B IDs and PIDs, the Sibyl memory/journal IDs, exit confirmation, retrieval event, and Base status. Expand Technical Evidence for query scores and safety policy.
9. Approve the simulated response; explain that no production action runs.
10. If the Base contract is configured, connect an operator wallet, anchor, and show the verified transaction. Otherwise show `NOT ANCHORED`.

CLI proof: `python scripts/fresh_session_smoke.py`.
