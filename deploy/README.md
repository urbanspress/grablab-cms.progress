# Deploying GrabLab CMS `v1.0.0` (Docker `--read-only` & Grisp Production Guide)

This directory contains the hardened production deployment template for **GrabLab CMS `v1.0.0`**, built on **GRAB (`>= v1.0.1`, verified on `1.1.0`)**, **Grisp**, and **Grex JS `v1.0.0`**.

> **Zero-Secrets Git Policy:** Never commit real server IP addresses, private domains, database passwords, OAuth secrets, or `GRABLAB_MASTER_KEY` values to Git. Supply all secrets via an untracked `.env` file or your container secret manager.

---

## 1. Architecture of the `--read-only` Profile

[`docker-compose.yml`](docker-compose.yml) runs the container root filesystem in strict read-only mode (`read_only: true`, equivalent to `docker run --read-only`), drops all Linux capabilities (`cap_drop: ["ALL"]`), disables privilege escalation (`no-new-privileges:true`), and permits writes **only** to three host-mounted runtime paths:

| Host Path | Container Path | Purpose | GRAB Permission / Env Link |
|---|---|---|---|
| `../storage` | `/app/storage` | SQLite database file (`storage/grablab.db`) when not using external PostgreSQL / MariaDB | `--db-config /app/grab.data.json --allow-db main:read-write` |
| `../uploads` *(or `../storage/uploads`)* | `/app/uploads` | Sanitized binary media uploads (`.png`, `.jpg`, `.webp`, `.gif`, `.pdf`) | `--allow-write /app/uploads` & `GRABLAB_UPLOAD_DIR=/app/uploads` |
| `../public/grex` | `/app/public/grex` | Served at `/static/grex/` — writable mount for Grex runtime bundles & Grex Theme Builder (`grex-builder`) `tokens.css` updates | `--allow-read /app` & `--static /app/public` (`server.asset`) |

If you prefer housing binary media inside `./storage/uploads`, adjust both the volume mount (`../storage/uploads:/app/storage/uploads:rw`), `GRABLAB_UPLOAD_DIR=/app/storage/uploads`, and `--allow-write /app/storage/uploads`.

---

## 2. Environment Setup (Copy, Never Commit `.env`)

Create an untracked `.env` file alongside `deploy/docker-compose.yml`:

```env
GRABLAB_IMAGE=grablab-cms:v1.0.0
GRABLAB_PORT=8080
GRABLAB_MASTER_KEY=replace-with-32-plus-random-bytes-at-runtime
GRABLAB_MAX_UPLOAD_BYTES=10485760
GRABLAB_TRUSTED_PROXY=127.0.0.1
GRABLAB_WORKERS=1
GRABLAB_WORKER_BASE_PORT=18080

# Optional: unattended first-run admin bootstrap (used only if users table is empty)
# GRABLAB_ADMIN_EMAIL=admin@example.com
# GRABLAB_ADMIN_PASSWORD=replace-with-strong-password
# GRABLAB_ADMIN_NAME=Site Administrator
```

---

## 3. First-Time Database Migration & Seed

Run cumulative migrations (`001` → `002` → `003`) and idempotent starter seeding once before accepting traffic:

```sh
# 1. Apply migrations (SQLite default shown; swap grab.data.json for PostgreSQL/MariaDB)
grab migrate --db-config /app/grab.data.json --allow-db main:migrate /app/migrations/001_schema.grab
grab migrate --db-config /app/grab.data.json --allow-db main:migrate /app/migrations/002_auth_schema.grab
grab migrate --db-config /app/grab.data.json --allow-db main:migrate /app/migrations/003_v04_schema.grab

# (Or run 003_v04_schema.grab directly on a fresh empty database, as it includes versions [1, 2, 3].)
# For PostgreSQL: use migrations/003_v04_schema_postgres.grab
# For MariaDB:    use migrations/003_v04_schema_mariadb.grab

# 2. Optional idempotent starter content, fields, categories & menus
grab run --db-config /app/grab.data.json --allow-db main:read-write /app/migrations/seed.grab
```

---

## 4. Direct CLI (`--read-only` Container / Grisp Bare-Metal)

Equivalent direct `docker run` pattern matching `docker-compose.yml`:

```sh
docker run --rm -d \
  --name grablab-cms \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  -p 127.0.0.1:8080:8080 \
  -v "$(pwd)/storage:/app/storage:rw" \
  -v "$(pwd)/uploads:/app/uploads:rw" \
  -v "$(pwd)/public/grex:/app/public/grex:rw" \
  -e GRABLAB_MASTER_KEY="$GRABLAB_MASTER_KEY" \
  -e GRABLAB_UPLOAD_DIR="/app/uploads" \
  -e GRABLAB_MAX_UPLOAD_BYTES="10485760" \
  grablab-cms:v1.0.0 \
  grab serve \
    --addr 0.0.0.0:8080 \
    --allow-public \
    --allow-scripts \
    --diagnostics production \
    --log-format json \
    --trusted-proxy 127.0.0.1 \
    --allow-read /app \
    --allow-write /app/uploads \
    --allow-env GRABLAB_MASTER_KEY,GRABLAB_UPLOAD_DIR,GRABLAB_MAX_UPLOAD_BYTES \
    --db-config /app/grab.data.json \
    --allow-db main:read-write \
    --platform-config /app/grab.platform.json \
    --allow-cache cms:read-write \
    --allow-cache cms:limit \
    --static /app/public \
    --max-body-bytes 15728640 \
    /app/src/app.grab
```

### Multi-Worker Grisp Scaling (`--workers`)
- Pass `--workers <N> --worker-base-port 18080` to fan out concurrent Grisp HTTP workers on consecutive loopback ports (`18080..18080+N-1`) behind an external upstream balancer (Caddy or Nginx).
- For multi-worker deployments (`N > 1`), switch `grab.data.json` to PostgreSQL or MariaDB and set `--trusted-proxy` to your upstream balancer's loopback/private CIDR.

### Opt-In Zero-Plugin E-Commerce Webhook Profile (`v1.1.0`)
- Standard CMS deployments use `grab.platform.json` with zero required webhook secrets.
- When enabling storefront checkout and signed payment webhooks:
  1. Run schema migration `004` (`migrations/004_commerce_schema.grab`) and `migrations/seed_commerce.grab`.
  2. Prepare GRAB's native `commerce` event inbox tables:
     ```sh
     grab migrate --platform-config deploy/grab.platform.commerce.json --db-config grab.data.json --events-store commerce --allow-db main:migrate --allow-events commerce:work
     ```
  3. Set `GRABLAB_PAYMENT_WEBHOOK_SECRET` (>= 16 chars) in environment variables (and optionally add `"GRABLAB_PAYMENT_WEBHOOK_SECRET_NEXT"` to `deploy/grab.platform.commerce.json` `webhooks.payment.keys` during key rotation).
  4. Boot with `--platform-config deploy/grab.platform.commerce.json --allow-env ...,GRABLAB_PAYMENT_WEBHOOK_SECRET --allow-events commerce:accept --allow-events commerce:work`.
  5. **Important Multi-Worker Note:** GRAB's SQLite event store is single-process. Production stores running `--workers > 1` while accepting webhooks MUST configure PostgreSQL or MariaDB in `grab.data.json`.
  6. **Optional External Sweep Cron:** Traffic-driven commerce sweeps run automatically (`<= 1` run per 5 min across all workers); high-volume sites may also trigger `grab run --db-config grab.data.json --allow-db main:read-write scripts/commerce_sweep.grab`.

### Health & Readiness Checks
- **Liveness:** `GET /_health` → `200 OK` (`{"status":"ok"}`)
- **Readiness:** `GET /_ready` → `200 OK` (`{"status":"ready","in_flight":0,"max_concurrency":64}`)
