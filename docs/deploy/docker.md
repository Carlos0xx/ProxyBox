# Docker Compose

The `docker-compose.yml` at the repo root ships a four-service stack:

| Service | Image | Role |
|---|---|---|
| `bootstrap` | `proxybox:local` (built locally) | one-shot config generator |
| `sing-box` | `ghcr.io/sagernet/sing-box:latest` | the proxy |
| `proxybox-admin` | `proxybox:local` | FastAPI admin |
| `proxybox-traffic-worker` | `proxybox:local` | Clash API polling |
| `proxybox-bot` (profile `bot`) | `proxybox:local` | Telegram bot |

```bash
docker compose up -d
docker compose ps
docker compose exec proxybox-admin grep token /etc/proxybox/config.yaml
```

Volumes: `proxybox-config`, `proxybox-data`, `proxybox-sub`, `singbox-config`.

Limitations vs `install.sh`: no fail2ban, no automatic TLS. Pair with an
external Caddy / nginx / Cloudflare Tunnel for production.
