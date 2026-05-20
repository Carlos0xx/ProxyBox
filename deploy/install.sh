#!/usr/bin/env bash
# ProxyBox installer — sets up a fresh Debian/Ubuntu VPS.
#
# Usage:
#   git clone https://github.com/carlos0xx/proxybox /opt/proxybox
#   cd /opt/proxybox && sudo bash deploy/install.sh
#
# Idempotent: re-running it on an existing install does nothing destructive,
# only fills in missing pieces. Safe to run repeatedly.

set -euo pipefail

# ─── config (overridable via env) ──────────────────────────────────
: "${PROXYBOX_DIR:=$(cd "$(dirname "$0")/.." && pwd)}"
: "${CONFIG_DIR:=/etc/proxybox}"
: "${DATA_DIR:=/var/lib/proxybox}"
: "${LOG_DIR:=/var/log/proxybox}"
: "${SUB_DIR:=/var/www/proxybox-sub}"
: "${SINGBOX_DIR:=/etc/sing-box}"

# ─── sentinel: this looks like a ProxyBox checkout ─────────────────
if [ ! -f "$PROXYBOX_DIR/pyproject.toml" ]; then
    echo "ERROR: PROXYBOX_DIR=$PROXYBOX_DIR doesn't look like a ProxyBox checkout" >&2
    echo "       expected pyproject.toml at \$PROXYBOX_DIR/" >&2
    exit 1
fi

# ─── pre-flight: defer to check-prereqs.sh (skippable for hot-paths) ──
#
# This validates OS / arch / privilege / RAM / disk / network / systemd /
# ports / required apt packages BEFORE we touch anything destructive.
# Skip with PROXYBOX_SKIP_PREREQ=1 only if you've just run check-prereqs.sh
# yourself and know what you're doing.
if [ "${PROXYBOX_SKIP_PREREQ:-0}" != "1" ]; then
    if ! bash "$PROXYBOX_DIR/deploy/check-prereqs.sh"; then
        echo ""
        echo "ERROR: pre-flight check failed. fix the issues above and re-run." >&2
        echo "       (to install missing apt packages automatically:" >&2
        echo "         sudo bash $PROXYBOX_DIR/deploy/check-prereqs.sh --install)" >&2
        exit 1
    fi
fi

echo ""
echo "==> ProxyBox installer"
echo "    source:     $PROXYBOX_DIR"
echo "    config:     $CONFIG_DIR"

# ─── 1. system packages ────────────────────────────────────────────
echo "==> installing system packages..."
apt-get -y update >/dev/null
apt-get -y install \
    python3 python3-venv python3-pip python3-systemd \
    curl sqlite3 openssl fail2ban \
    >/dev/null

# ─── 2. directories ────────────────────────────────────────────────
mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR" "$SUB_DIR" "$SINGBOX_DIR"

# ─── 3. sing-box binary ────────────────────────────────────────────
if ! command -v sing-box >/dev/null; then
    echo "==> installing sing-box..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)         ARCH=amd64 ;;
        aarch64|arm64)  ARCH=arm64 ;;
        *) echo "ERROR: unsupported arch $ARCH" >&2; exit 1 ;;
    esac
    RESP=$(curl -fsSL "https://api.github.com/repos/SagerNet/sing-box/releases/latest")
    SBVER=$(printf '%s\n' "$RESP" | grep '"tag_name":' | head -1 | cut -d'"' -f4)
    cd /tmp
    curl -fsSLO "https://github.com/SagerNet/sing-box/releases/download/${SBVER}/sing-box-${SBVER#v}-linux-${ARCH}.tar.gz"
    tar -xzf "sing-box-${SBVER#v}-linux-${ARCH}.tar.gz"
    install -m 755 "sing-box-${SBVER#v}-linux-${ARCH}/sing-box" /usr/local/bin/sing-box
    rm -rf "/tmp/sing-box-${SBVER#v}"*
fi
echo "    sing-box: $(sing-box version | head -1)"

# ─── 4. sing-box systemd unit ──────────────────────────────────────
if [ ! -f /etc/systemd/system/sing-box.service ]; then
    cat > /etc/systemd/system/sing-box.service <<'UNIT'
[Unit]
Description=sing-box service
Documentation=https://sing-box.app
After=network.target

[Service]
Type=simple
NoNewPrivileges=yes
ExecStart=/usr/local/bin/sing-box run -c /etc/sing-box/config.json
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=3s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload
fi

# ─── 5. sing-box config (only generate if missing) ────────────────
if [ ! -f "$SINGBOX_DIR/config.json" ]; then
    echo "==> generating Reality keypair + Hy2 cert + random SNI..."
    KEYPAIR=$(sing-box generate reality-keypair)
    PRIVATE_KEY=$(printf '%s\n' "$KEYPAIR" | awk '/PrivateKey/{print $2}')
    SHORT_ID=$(openssl rand -hex 8)
    HY2_OBFS_PW=$(openssl rand -hex 16)

    SNI_CANDIDATES=(www.microsoft.com www.apple.com www.cloudflare.com www.amazon.com)
    SNI="${SNI_CANDIDATES[$RANDOM % 4]}"

    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -keyout "$SINGBOX_DIR/key.pem" -out "$SINGBOX_DIR/cert.pem" \
        -subj "/CN=$SNI" 2>/dev/null
    chmod 600 "$SINGBOX_DIR/key.pem"

    cat > "$SINGBOX_DIR/config.json" <<JSON
{
  "log": { "level": "info", "timestamp": true },
  "experimental": {
    "clash_api": { "external_controller": "127.0.0.1:9090" }
  },
  "inbounds": [
    {
      "type": "vless",
      "tag": "vless-template",
      "listen": "::",
      "listen_port": 11000,
      "users": [],
      "tls": {
        "enabled": true,
        "server_name": "$SNI",
        "reality": {
          "enabled": true,
          "handshake": { "server": "$SNI", "server_port": 443 },
          "private_key": "$PRIVATE_KEY",
          "short_id": ["$SHORT_ID"]
        }
      }
    },
    {
      "type": "hysteria2",
      "tag": "hy2-template",
      "listen": "::",
      "listen_port": 21000,
      "users": [],
      "obfs": { "type": "salamander", "password": "$HY2_OBFS_PW" },
      "tls": {
        "enabled": true,
        "alpn": ["h3"],
        "certificate_path": "$SINGBOX_DIR/cert.pem",
        "key_path": "$SINGBOX_DIR/key.pem"
      },
      "masquerade": "https://$SNI"
    }
  ],
  "outbounds": [{ "type": "direct", "tag": "direct" }]
}
JSON
    chmod 600 "$SINGBOX_DIR/config.json"
    sing-box check -c "$SINGBOX_DIR/config.json"
fi

# ─── 6. Python venv + deps ─────────────────────────────────────────
cd "$PROXYBOX_DIR"
if [ ! -d .venv ]; then
    echo "==> creating Python venv..."
    python3 -m venv .venv
fi
echo "==> installing ProxyBox deps..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

# ─── 7. ProxyBox config.yaml ───────────────────────────────────────
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo "==> generating ProxyBox config..."
    ADMIN_TOKEN=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(24))")
    PUBLIC_HOST=$(curl -fsS --max-time 5 https://ifconfig.me 2>/dev/null \
                 || curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null \
                 || echo "")
    cat > "$CONFIG_DIR/config.yaml" <<YAML
admin:
  token: "$ADMIN_TOKEN"
  host: "0.0.0.0"
  port: 8080
server:
  public_host: "$PUBLIC_HOST"
paths:
  traffic_db: $DATA_DIR/traffic.db
  static_dir: $PROXYBOX_DIR/static
  sub_dir: $SUB_DIR
  singbox_config: $SINGBOX_DIR/config.json
  session_secret: $CONFIG_DIR/session-secret
services:
  monitored:
    - sing-box
    - proxybox-admin
    - proxybox-traffic-worker
    - fail2ban
ports:
  vless_range: [11001, 11050]
  hy2_range: [21001, 21050]
clash:
  api_url: "http://127.0.0.1:9090"
  api_secret: ""
worker:
  poll_interval: 10
  retention_days: 7
passkey:
  rp_id: ""
  rp_name: "ProxyBox"
  origin: ""
features:
  passkey: false
  bot: false
YAML
    chmod 600 "$CONFIG_DIR/config.yaml"
fi

# ─── 8. fail2ban [manual] jail ─────────────────────────────────────
if ! grep -q '^\[manual\]' /etc/fail2ban/jail.local 2>/dev/null; then
    cat > /etc/fail2ban/jail.local <<'JAIL'
# ProxyBox manual ban jail — explicit ban via /action/block.
# backend=systemd avoids /var/log/auth.log dependency (Debian 13 = journald-only).
[manual]
enabled  = true
backend  = systemd
filter   = sshd
action   = iptables-allports[name=manual]
bantime  = -1
findtime = 60
maxretry = 99999
JAIL
fi

# ─── 9. ProxyBox admin systemd unit ────────────────────────────────
if [ ! -f /etc/systemd/system/proxybox-admin.service ]; then
    cat > /etc/systemd/system/proxybox-admin.service <<UNIT
[Unit]
Description=ProxyBox admin HTTP API
After=network.target sing-box.service
Wants=sing-box.service

[Service]
Type=simple
WorkingDirectory=$PROXYBOX_DIR
Environment=PROXYBOX_CONFIG=$CONFIG_DIR/config.yaml
ExecStart=$PROXYBOX_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5s
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload
fi

# ─── 10. other systemd units (worker + bot) ────────────────────────
for unit in proxybox-traffic-worker.service proxybox-bot.service; do
    src="$PROXYBOX_DIR/deploy/systemd/$unit"
    dst="/etc/systemd/system/$unit"
    if [ -f "$src" ] && [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        systemctl daemon-reload
    fi
done

# ─── 11. enable + start core services ──────────────────────────────
echo "==> starting services..."
systemctl enable --now fail2ban  >/dev/null 2>&1 || true
systemctl enable --now sing-box  >/dev/null 2>&1 || true
systemctl enable --now proxybox-admin >/dev/null 2>&1 || true
systemctl enable --now proxybox-traffic-worker >/dev/null 2>&1 || true
sleep 3

# ─── 12. summary ───────────────────────────────────────────────────
ADMIN_TOKEN=$(.venv/bin/python -c "import yaml; print(yaml.safe_load(open('$CONFIG_DIR/config.yaml'))['admin']['token'])")
PUBLIC_HOST=$(.venv/bin/python -c "import yaml; print(yaml.safe_load(open('$CONFIG_DIR/config.yaml'))['server']['public_host'])")
TOKEN_PREFIX="${ADMIN_TOKEN:0:8}"

echo ""
echo "============================================================"
echo "  ProxyBox installed"
echo "============================================================"
echo "  admin URL:  http://${PUBLIC_HOST:-<your-vps-ip>}:8080/admin/${TOKEN_PREFIX}.../"
echo "  full token: $CONFIG_DIR/config.yaml  (admin.token field)"
echo ""
echo "  services:"
for svc in sing-box proxybox-admin proxybox-traffic-worker fail2ban; do
    state=$(systemctl is-active "$svc" 2>/dev/null || echo unknown)
    case "$state" in
        active)   mark="[+]" ;;
        inactive) mark="[-]" ;;
        *)        mark="[?]" ;;
    esac
    printf "    %s %-30s %s\n" "$mark" "$svc" "$state"
done
echo ""
echo "  next:"
echo "    1. grep token in $CONFIG_DIR/config.yaml — save it offline"
echo "    2. open the admin URL above (HTTP for now; set up Caddy + Let's Encrypt for production)"
echo "    3. in the admin UI, click '+ 添加设备' to create your first device"
echo "    4. scan QR / copy subscription URL into a sing-box-compatible client"
echo ""
echo "  optional features:"
echo "    - passkey:  set features.passkey=true + passkey.rp_id/origin in config.yaml + Caddy/TLS"
echo "    - TG bot:   fill /etc/proxybox/bot.env then 'systemctl enable --now proxybox-bot'"
echo "============================================================"
