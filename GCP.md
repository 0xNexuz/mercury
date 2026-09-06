# Google Cloud judge deployment

MERCURY keeps its official Sibyl SQLite/FTS5 database on a single persistent Google Compute Engine VM while Vercel serves the dashboard.

Use one free-tier eligible `e2-micro` in `us-west1`, `us-central1`, or `us-east1`, with at most 30 GB `pd-standard`, Standard network tier, and only one API process. Google requires billing activation; budgets are alerts, not hard spending caps.

Use `deploy/gcp/bootstrap.sh` as the startup script. It serves the API at `https://<external-ip>.sslip.io`, writes that URL to `/etc/mercury/public-api-url`, and stores Sibyl at `/data/memory.db`.

Set `MERCURY_API_ORIGIN` to that HTTPS origin in Vercel and redeploy production. After a real Base Sepolia contract deployment, set the identical address as backend `BASE_RECEIPTS_CONTRACT` and frontend `NEXT_PUBLIC_BASE_RECEIPTS_CONTRACT`.

The deployment remains **UNVERIFIED** until the public Session A/B flow, refresh recovery, and VM reboot recovery have all passed.
