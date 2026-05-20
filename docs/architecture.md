# Architecture

ProxyBox is four processes coordinating through one SQLite database and a
sing-box-generated JSON config:

```
┌─ /etc/sing-box/config.json ────────────────────────┐
│ template inbounds (vless-template, hy2-template) +  │
│ per-device inbounds (vless-{name}, hy2-{name})     │
└────────────────────┬───────────────────────────────┘
                     │
            ┌────────┴────────┐
            │                 │
            ▼                 ▼
   ┌──────────────┐   ┌─────────────────────────┐
   │   sing-box   │   │  proxybox-admin (HTTP)  │
   │  (systemd)   │   │  - reads sing-box config │
   │              │   │  - writes per-device inb │
   └──────┬───────┘   └──────────┬──────────────┘
          │                      │
          │ Clash API            │ admin token URL path
          │ /connections         │ /admin/{token}/...
          │                      │
          ▼                      ▼
   ┌────────────────┐   ┌────────────────┐
   │ traffic-worker │   │  Admin SPA     │
   │ polls every 10s│   │  /admin/{tok}/ │
   │  → traffic_log │   │  React-ish JS  │
   └────────┬───────┘   └────────────────┘
            │
            ▼
   ┌────────────────────────────────────┐
   │     /var/lib/proxybox/traffic.db   │
   │  device (CRUD)                     │
   │  traffic_log (per device × hour)   │
   │  passkey_credential (opt-in)       │
   └────────────────────────────────────┘
```

## Processes

| Process | Source | systemd unit | Purpose |
|---|---|---|---|
| sing-box | upstream binary | `sing-box.service` | The actual proxy. Configured via `/etc/sing-box/config.json`. |
| proxybox-admin | `app/main.py` | `proxybox-admin.service` | FastAPI app, 34 admin endpoints + GET / serving the SPA. |
| proxybox-traffic-worker | `app/workers/traffic.py` | `proxybox-traffic-worker.service` | Polls sing-box Clash API, writes byte deltas to SQLite. |
| proxybox-bot (opt-in) | `bot/__main__.py` | `proxybox-bot.service` | Telegram long-poll, 7 commands. |
| fail2ban | apt package | `fail2ban.service` | Manual IP ban backend (custom `[manual]` jail, backend=systemd). |

## Database

Single SQLite file at `/var/lib/proxybox/traffic.db`, three tables:

```sql
CREATE TABLE device (
  name          TEXT     PRIMARY KEY,    -- "phone-1", "laptop", etc.
  label         TEXT     NOT NULL,        -- human-friendly display name
  kind          TEXT     NOT NULL,        -- "mobile" / "desktop" / "router"
  vless_uuid    TEXT     NOT NULL,        -- 128-bit RFC 4122 v4
  hy2_password  TEXT     NOT NULL,        -- 24-byte url-safe random
  vless_port    INTEGER  NOT NULL,        -- per-device TCP port
  hy2_port      INTEGER  NOT NULL,        -- per-device UDP port
  sni           TEXT     NOT NULL,        -- Reality cover-domain
  created_at    INTEGER  NOT NULL,
  last_seen     INTEGER,                  -- updated by traffic-worker
  last_ip       TEXT,                     -- last source IP seen
  revoked       INTEGER  NOT NULL DEFAULT 0,
  notes         TEXT     NOT NULL DEFAULT '',
  sub_token     TEXT     NOT NULL UNIQUE, -- subscription URL secret
  paused_until  INTEGER  NOT NULL DEFAULT 0
);

CREATE TABLE traffic_log (
  device_name  TEXT    NOT NULL,
  bucket_ts    INTEGER NOT NULL,  -- UTC hour-aligned epoch
  date         TEXT    NOT NULL,  -- YYYY-MM-DD UTC
  hour         INTEGER NOT NULL,  -- 0-23 UTC
  rx_bytes     INTEGER NOT NULL,  -- download (server→client)
  tx_bytes     INTEGER NOT NULL,  -- upload (client→server)
  conn_count   INTEGER NOT NULL,  -- number of new connections in bucket
  PRIMARY KEY (device_name, bucket_ts)
);

CREATE TABLE passkey_credential (
  credential_id  TEXT     PRIMARY KEY,
  public_key     BLOB     NOT NULL,
  sign_count     INTEGER  NOT NULL,
  label          TEXT     NOT NULL DEFAULT '',
  created_at     INTEGER  NOT NULL,
  last_used_at   INTEGER
);
```

Migrations are additive only. The schema lives in `app/db/schema.sql` and
re-runs every app startup via `init_schema()` (all statements use
`IF NOT EXISTS`).

## URL layout

| Path | Auth | Purpose |
|---|---|---|
| `GET /admin/{token}/` | URL token | SPA HTML (token substituted into JS) |
| `GET /admin/{token}/api/status` | URL token | system + service stats |
| `GET /admin/{token}/api/devices` | URL token | per-device current usage |
| `POST /admin/{token}/api/devices/new` | URL token | create device (allocates ports, generates UUID, writes config + sub file) |
| `POST /admin/{token}/api/devices/{name}/pause` | URL token | remove inbounds + set `paused_until` |
| `POST /admin/{token}/api/devices/{name}/resume` | URL token | restore inbounds |
| `POST /admin/{token}/api/devices/{name}/delete` | URL token | hard delete (DB + config + sub file) |
| `GET /api/sub/{sub_token}` | **public** (sub_token IS the secret) | client subscription URL list |
| `GET /admin/{token}/api/history/devices?days=N` | URL token | per-device daily totals |
| `POST /admin/{token}/action/rotate` | URL token + body confirm | Reality keypair rotation |
| `GET /admin/{token}/api/logs/{svc}` | URL token (svc in allowlist) | journalctl wrapper |
| `POST /auth/webauthn/login/begin` (opt-in) | none (passkey is the auth) | WebAuthn challenge |

Full list: [API · Endpoints](./api/endpoints).

## Design choices vs other proxy panels

| Choice | What we did | Why |
|---|---|---|
| Per-device inbound | unique vless/hy2 port + UUID per device | revoke surgically, accurate traffic accounting per device |
| Traffic source | sing-box Clash API (not nftables) | no kernel-level firewall rules to manage, single source of truth, runs in Docker |
| Subscription path | plain HTTP `text/plain` URI list at `/api/sub/{token}` | maximum client compatibility; Shadowrocket etc. don't all support raw vless:// paste |
| Admin auth | URL-path token by default, opt-in WebAuthn passkey | URL works in bookmark-able links; passkey adds 2nd factor |
| Reality cover-domain | random pick from `www.microsoft.com / apple.com / cloudflare.com / amazon.com` per install | no shared fingerprint across deployments |
| Per-host classifier | **dropped** (vs BWG upstream) | host-level data is a fingerprint; aggregating per-device only is privacy-preserving |
| install.sh idempotency | every step gated by existence check | safe to re-run, can resume after partial failure |
