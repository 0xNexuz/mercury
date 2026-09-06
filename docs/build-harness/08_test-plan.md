# Test plan

Required gates:

```powershell
.\.venv\Scripts\python -m pytest api\tests
.\.venv\Scripts\ruff check api evals scripts
npm run lint
npm run typecheck
npm test
npm run build
.\.venv\Scripts\python scripts\fresh_session_smoke.py
.\.venv\Scripts\python evals\run_benchmark.py
```

Public gates add health, A/B proof, refresh recovery, concurrent judge isolation, API restart, VM reboot, and secret scanning. Base adds a real testnet deploy, emitted-value verification, and rejection tests for wrong chain, contract, event, or hashes.

Current evidence: backend 16/16 and frontend 4/4 passed on 2026-09-06. Remaining commands must be rerun after deployment changes.
