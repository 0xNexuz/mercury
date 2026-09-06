# Hosted judge proof

## Why Vercel alone is not the memory backend

Vercel Functions do not provide a shared durable filesystem. A SQLite file written by one invocation can disappear with that instance and cannot be shared reliably across scaled instances. MERCURY therefore keeps Vercel as an optional frontend only; it never places Sibyl's `memory.db` inside a Vercel Function.

Sibyl's official local client is intentionally SQLite/FTS5 and local-first. The hosted backend must consequently be a single persistent service with a durable volume mounted at `/data`, with `SIBYL_DB_PATH=/data/memory.db`.

## Delivery paths

- **Immediate public judge path:** the native FastAPI and production Next.js processes share the real Sibyl file under `data/memory.db`; Cloudflare Tunnel exposes one same-origin HTTPS URL. Browser and API restarts do not erase the file. A Quick Tunnel URL lasts only while the launcher remains running.
- **Preferred free-tier judge path:** one Google Compute Engine `e2-micro`, a standard persistent boot disk, and one FastAPI process with `SIBYL_DB_PATH=/data/memory.db`. Caddy supplies HTTPS and Vercel proxies `/api/*` through `MERCURY_API_ORIGIN`. See [GCP.md](GCP.md).
- **Free-tier fallback:** one Oracle Always Free VM with persistent block storage. Capacity can be unavailable and idle resources can be reclaimed.
- **Paid managed path:** one Railway or Render service, one persistent `/data` volume, and one replica.
- **Reproduction paths retained:** Docker Compose uses the `mercury-sibyl` named volume; native smoke tests use an explicit database path.

Official constraints: [Sibyl Memory](https://github.com/Sibyl-Labs/Sibyl-Memory), [Vercel SQLite guidance](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel), [Google Cloud Free Tier](https://cloud.google.com/free/docs/free-cloud-features), and [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

## Proof isolation and red-team controls

`POST /api/proof-runs` creates an unguessable proof-run identifier and a dedicated Sibyl tenant in the same database. Session A and Session B are separate Python worker processes. The orchestrator waits for Session A's exit code before permitting Session B. The browser keeps only the active response and a proof-run locator in the URL; refresh reconstructs the inspector from Sibyl.

- Cross-judge leakage: unique Sibyl tenant per random run ID.
- Session reuse: worker PIDs and UUID session IDs must differ; the parent records the real exit code.
- Hidden hardcoding: Session B invokes the same incident analysis path and must cite Session A's Sibyl entity ID.
- Race conditions: a per-run lock rejects duplicate phase execution; separate judge runs remain concurrent.
- Memory failure: write/read/retrieval mismatches fail closed and cannot produce `passed`.
- Refresh/restart: proof retrieval is from Sibyl; the API process stores no durable proof state.
- Base claims: commitments remain `UNANCHORED` until the existing verifier confirms a real Base Sepolia receipt.
- Secrets: proof output contains no credentials, wallet secrets, or environment values.
