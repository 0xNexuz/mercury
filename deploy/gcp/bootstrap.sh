#!/usr/bin/env bash
set -euo pipefail

# Run as the startup script on one free-tier eligible e2-micro Ubuntu VM.
# The persistent VM disk holds Sibyl at /data/memory.db.

REPO_URL="${MERCURY_REPO_URL:-https://github.com/0xNexuz/mercury.git}"
REPO_BRANCH="${MERCURY_REPO_BRANCH:-build/mercury-v1}"
WEB_ORIGIN="${MERCURY_WEB_ORIGIN:-https://mercury-ir.vercel.app}"
APP_DIR=/opt/mercury
CONFIG_DIR=/etc/mercury

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl docker.io git
systemctl enable --now docker
install -d -m 0755 "$CONFIG_DIR" /data
install -d -m 0755 /var/lib/mercury-caddy/data /var/lib/mercury-caddy/config

if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR"
  git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch --depth 1 origin "$REPO_BRANCH"
  git -C "$APP_DIR" checkout --detach FETCH_HEAD
fi

docker build --pull -f "$APP_DIR/Dockerfile.api" -t mercury-api:current "$APP_DIR"

if [ ! -f "$CONFIG_DIR/api.env" ]; then
  cat >"$CONFIG_DIR/api.env" <<EOF
SIBYL_DB_PATH=/data/memory.db
SIBYL_TENANT_ID=mercury
WEB_ORIGIN=$WEB_ORIGIN
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
BASE_RECEIPTS_CONTRACT=
EOF
  chmod 0600 "$CONFIG_DIR/api.env"
fi

PUBLIC_IP="$(curl -fsS -H 'Metadata-Flavor: Google' 'http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip')"
PUBLIC_HOST="${PUBLIC_IP}.sslip.io"

cat >"$CONFIG_DIR/Caddyfile" <<EOF
$PUBLIC_HOST {
  encode zstd gzip
  reverse_proxy 127.0.0.1:8000
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "no-referrer"
  }
}
EOF

cat >/etc/systemd/system/mercury-api.service <<'EOF'
[Unit]
Description=MERCURY FastAPI and Sibyl Memory
After=docker.service network-online.target
Requires=docker.service

[Service]
Restart=always
RestartSec=5
ExecStartPre=-/usr/bin/docker rm -f mercury-api
ExecStart=/usr/bin/docker run --name mercury-api --env-file /etc/mercury/api.env -p 127.0.0.1:8000:8000 -v /data:/data mercury-api:current
ExecStop=/usr/bin/docker stop mercury-api

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/mercury-caddy.service <<'EOF'
[Unit]
Description=MERCURY HTTPS reverse proxy
After=docker.service network-online.target mercury-api.service
Requires=docker.service mercury-api.service

[Service]
Restart=always
RestartSec=5
ExecStartPre=-/usr/bin/docker rm -f mercury-caddy
ExecStart=/usr/bin/docker run --name mercury-caddy --network host -v /etc/mercury/Caddyfile:/etc/caddy/Caddyfile:ro -v /var/lib/mercury-caddy/data:/data -v /var/lib/mercury-caddy/config:/config caddy:2-alpine
ExecStop=/usr/bin/docker stop mercury-caddy

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now mercury-api mercury-caddy
printf 'https://%s\n' "$PUBLIC_HOST" | tee "$CONFIG_DIR/public-api-url"

for attempt in $(seq 1 30); do
  if curl -fsS "https://${PUBLIC_HOST}/api/health" >/dev/null; then
    echo "MERCURY API ready: https://${PUBLIC_HOST}"
    exit 0
  fi
  sleep 5
done

echo "MERCURY API did not become healthy" >&2
systemctl --no-pager --full status mercury-api mercury-caddy >&2 || true
exit 1
