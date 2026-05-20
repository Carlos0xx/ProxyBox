# Getting started

ProxyBox runs on a single VPS. It binds three TCP ports (8080 admin, 11001-11050
for VLESS, 21001-21050 for Hysteria2 UDP) and serves clients that speak
sing-box-compatible protocols.

## Prerequisites

- Debian 12+ or Ubuntu 22.04+ VPS (Docker path also works on macOS dev machines)
- SSH access with root (or sudo without password prompt)
- At least 1 GB RAM and 5 GB free disk
- Open ports on the VPS firewall: 8080 (admin), 11001-11050 (TCP, VLESS),
  21001-21050 (UDP, Hy2)

## Path 1 — `install.sh` (recommended for Linux VPS)

```bash
git clone https://github.com/carlos0xx/proxybox /opt/proxybox
cd /opt/proxybox
sudo bash deploy/install.sh
```

The installer:

1. `apt install` python3-venv + curl + fail2ban + sqlite3 + openssl
2. Pulls latest `sing-box` from GitHub releases (auto-detects amd64/arm64)
3. Generates Reality keypair, Hy2 self-signed cert, random SNI from a public-domain pool
4. Writes `/etc/sing-box/config.json` and `/etc/proxybox/config.yaml`
5. Provisions four systemd units (sing-box, proxybox-admin, proxybox-traffic-worker, fail2ban)
6. Starts everything

Re-running is safe — every step is gated by `[ ! -f ... ]` or `if ! command -v ... `.

## Path 2 — Docker Compose

```bash
git clone https://github.com/carlos0xx/proxybox && cd proxybox
docker compose up -d
```

The compose stack uses a one-shot `bootstrap` container to generate configs
before the runtime services start. Volumes persist across restarts.

To also start the Telegram bot:

```bash
# fill BOT_TOKEN + TG_ALLOWED_USERS + ADMIN_TOKEN into /etc/proxybox/bot.env first
docker compose --profile bot up -d proxybox-bot
```

Limitations of the Docker path:

- No fail2ban (host iptables not exposed to containers)
- No automatic Caddy / HTTPS termination

## Path 3 — Claude Code

If you have Claude Code installed:

```bash
mkdir -p ~/.claude/skills/proxybox-deploy
cp -r deploy/claude-skill/* ~/.claude/skills/proxybox-deploy/
```

Then ask Claude:

> deploy proxybox on my VPS at 1.2.3.4 using ~/.ssh/id_ed25519

Claude walks through pre-flight checks, ships the code, runs `install.sh`,
verifies all four services, and reports back the admin URL (with token
masked to first 8 chars).

## After install — first device

1. SSH in and read your admin token: `grep token /etc/proxybox/config.yaml`
2. Open `http://<your-vps>:8080/admin/<token>/` in a browser
3. Click "+ 添加设备", give it a name like `my-phone`
4. Copy the subscription URL shown in the response
5. Paste into a sing-box-compatible client (Shadowrocket on iOS,
   sing-box-for-android, Hiddify Next on desktop, etc.) as a **subscription
   URL** (not a single node)
6. Open the configured proxy and visit `https://ifconfig.me` — should
   return your VPS IP, not your home IP

## Next steps

- [Set up Caddy + Let's Encrypt](./deploy/install-sh#https-with-caddy) for HTTPS
- [Enable passkey login](./deploy/install-sh#passkey) (requires HTTPS)
- [Configure the Telegram bot](./deploy/install-sh#telegram-bot)
