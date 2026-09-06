# Evidence plan

| Claim | Required evidence | Status |
|---|---|---|
| Fresh process changes decision | A/B API response with distinct IDs/PIDs and cited Sibyl ID | VERIFIED locally |
| Persistence survives hosting restart | Same proof URL before/after VM reboot | MISSING P0 |
| Judges are isolated | Concurrent run evidence with distinct tenants/records | VERIFIED locally |
| Vercel serves current build | deployment URL and commit SHA | MISSING P0 |
| Base receipt is real | contract address, deployment tx, receipt tx, explorer URLs | MISSING |
| Benchmark is measured | generated JSON and Markdown | PRESENT; rerun pending |

Store public API responses, test logs, transaction metadata, and screenshots under `evidence/`. Never hand-author network evidence.
