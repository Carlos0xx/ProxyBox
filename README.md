# ProxyBox

> **Per-device 隔离的家用 / 个人 proxy 管理面板** · MIT License
>
> A self-hosted proxy admin panel that gives each device its own VLESS Reality
> + Hysteria2 inbound, byte-level traffic accounting, Telegram bot control,
> and (optional) WebAuthn passkey login — all on a single VPS.

<!-- Status badges go here once CI/CD is wired (Stage 6) -->

---

## ✨ What you get

- **Per-device inbounds** — every phone, laptop, router has its own UUID +
  port pair. No shared credentials, revoke any device individually without
  rotating everyone else.
- **VLESS Reality + Hysteria2** — one TCP path, one UDP path. Reality
  hides the inbound behind a real domain's TLS fingerprint (cloudflare /
  apple / microsoft picked at install). Hy2 picks up when UDP is the only
  thing not throttled.
- **Subscription URLs** — `GET /api/sub/{token}` serves a list of URIs
  any sing-box-compatible client (Shadowrocket, sing-box mobile, Hiddify,
  NekoBox, v2rayN) can import.
- **Per-device traffic** — a background worker polls sing-box's Clash
  API every 10 seconds and aggregates byte counts per UTC hour. SPA
  visualises the last 7 days; CSV export available.
- **Manual IP bans** — wrapped fail2ban, ban/unban via the admin API.
- **Optional Telegram bot** — `/status`, `/devices`, `/traffic`,
  `/pause`, `/resume`, `/bans` from your phone.
- **Optional WebAuthn passkey login** — Touch ID / Face ID / hardware
  key as the second auth path (URL token stays as the primary).
- **3 deploy paths** — shell, Docker, or Claude does it for you.

## 🚀 Quick start

Pick the path that matches your environment:

### Path A — `install.sh` (Debian / Ubuntu VPS, recommended)

```bash
ssh root@<your-vps>
git clone https://github.com/carlos0xx/proxybox /opt/proxybox
cd /opt/proxybox
bash deploy/install.sh
```

The script is idempotent — safe to re-run. It auto-detects your public IP,
generates a Reality keypair + Hy2 cert + random ADMIN_TOKEN, configures
fail2ban + 4 systemd units, and starts everything. Final output prints the
admin URL with the first 8 token chars; the full token is in
`/etc/proxybox/config.yaml`.

### Path B — Docker Compose

```bash
git clone https://github.com/carlos0xx/proxybox && cd proxybox
docker compose up -d                        # core stack (admin + worker + sing-box)
docker compose --profile bot up -d          # also start TG bot
docker compose exec proxybox-admin \
    grep token /etc/proxybox/config.yaml    # read your admin token
```

The `bootstrap` container generates configs on first start; volumes
preserve state across `docker compose down/up`. fail2ban is **not** included
in this path — pair with Caddy / a host firewall for production.

### Path C — Claude Code does it ("proxybox-deploy" skill)

```bash
mkdir -p ~/.claude/skills/proxybox-deploy
cp -r deploy/claude-skill/* ~/.claude/skills/proxybox-deploy/
```

Then in a Claude Code session:

> deploy proxybox on my VPS at 1.2.3.4 using ~/.ssh/id_ed25519

Claude walks through pre-flight checks, `git clone`, `install.sh`, and
verification. Admin token is **never** echoed in chat — Claude reports
only the first 8 chars and points you at the VPS config file.

## 📐 Architecture

```
┌─ Clients (iOS/Android/macOS/Win) ─┐
│  sing-box, Shadowrocket, Hiddify  │
└────────────────┬──────────────────┘
                 │ VLESS Reality (TCP 11001-11050)
                 │ Hysteria2 (UDP 21001-21050)
                 ▼
┌──────────────────────────────────┐
│           VPS                    │
│  ┌──────────────────────────┐    │
│  │  sing-box (systemd)      │◄───┼── Reality + Hy2 inbounds per device
│  └──────────┬───────────────┘    │
│             │ Clash API (127.0.0.1:9090)
│  ┌──────────▼───────────────┐    │
│  │ proxybox-traffic-worker  │    │── polls /connections every 10s
│  │   → traffic_log (SQLite) │    │
│  └──────────────────────────┘    │
│                                  │
│  ┌──────────────────────────┐    │
│  │  proxybox-admin (uvicorn)│◄───┼── Admin HTTP API + SPA on :8080
│  │  - 34 endpoints          │    │
│  │  - GET /api/sub/{token}  │    │── client subscription URL
│  │  - GET /admin/{token}/   │    │── HTML dashboard
│  └──────────────────────────┘    │
│                                  │
│  ┌──────────────────────────┐    │
│  │  proxybox-bot (optional) │    │── Telegram long-poll
│  └──────────────────────────┘    │
│                                  │
│  ┌──────────────────────────┐    │
│  │  fail2ban (manual jail)  │    │── iptables-allports on banned IPs
│  └──────────────────────────┘    │
└──────────────────────────────────┘
```

## 🧩 Configuration

Everything lives in `/etc/proxybox/config.yaml`. See
[`config.example.yaml`](./config.example.yaml) for the full schema with
inline comments. Highlights:

| Section | What it sets |
|---|---|
| `admin.token` | URL-path admin token. Read from env `ADMIN_TOKEN` via `${ADMIN_TOKEN}`. |
| `server.public_host` | Public IP/domain baked into subscription URIs. install.sh auto-fills. |
| `ports.vless_range` / `hy2_range` | Per-device port pools (inclusive). |
| `clash.api_url` | sing-box Clash API endpoint (default 127.0.0.1:9090). |
| `worker.poll_interval` / `retention_days` | Traffic accounting cadence + retention. |
| `features.passkey` / `features.bot` | Opt-in WebAuthn / Telegram. |
| `services.monitored` | Which systemd units `GET /api/status` checks. |

## 🛣️ Roadmap

| Stage | Status |
|---|---|
| 1 · code translation (admin / worker / passkey / bot) | ✅ |
| 2 · config abstraction + protocol simplification | ✅ |
| 3 · SPA `static/index.html` brand strip | ✅ |
| 4a · `install.sh` one-shot deploy | ✅ |
| 4b · Docker Compose | ✅ |
| 4c · Claude Skill bundle | ✅ |
| 5 · docs site (this README + VitePress) | 🔄 in progress |
| 6 · CI/CD (lint + test + multi-arch GHCR images + release) | ⏳ |
| 7 · security audit (`scripts/release-audit.sh`) | ⏳ |
| 8 · v0.1.0 release | ⏳ |

## 🔐 Security model

- **No SaaS dependency** — everything runs on the user's VPS.
- **URL-path admin token** — the path itself is the credential. Treat the
  admin URL like an API key.
- **Per-device credentials** — leaking one device's UUID/Hy2 password
  doesn't affect others. Revoke + regen-subs cleanly cuts off compromised
  devices.
- **Constant-time token comparison** — admin token check uses
  `secrets.compare_digest` to avoid timing attacks.
- **Atomic config writes** — config rotation uses tmp+rename so an aborted
  process can never leave a truncated `config.yaml`.
- **HTTP by default** — wrap with Caddy + Let's Encrypt for production.
  Passkey requires HTTPS (browser requirement).

## 📜 License

MIT — see [`LICENSE`](./LICENSE).
