---
layout: home
hero:
  name: ProxyBox
  text: Per-device isolated proxy panel
  tagline: VLESS Reality + Hysteria2, per-device inbounds, byte-level accounting, all on your VPS.
  actions:
    - theme: brand
      text: Quick start →
      link: /getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/carlos0xx/proxybox

features:
  - icon: 🔐
    title: Per-device credentials
    details: Each device gets its own UUID + ports. Revoke one without touching the others.

  - icon: 📊
    title: Real traffic accounting
    details: Background worker polls sing-box's Clash API, aggregates byte counts per UTC hour into SQLite. SPA shows 7-day chart per device + CSV export.

  - icon: 🤖
    title: Three deploy paths
    details: install.sh on Debian/Ubuntu, docker-compose anywhere, or let Claude Code drive the install via the bundled skill.

  - icon: 🛡️
    title: Optional passkey login
    details: WebAuthn (Touch ID / hardware key) as an alternative to the URL-path admin token. Off by default, flip features.passkey to enable.

  - icon: 📱
    title: Telegram bot control
    details: /status, /devices, /traffic, /pause, /resume, /bans from your phone. Opt-in, runs as its own systemd service.

  - icon: 🏠
    title: Designed for home use
    details: No SaaS, no API keys, no telemetry. Single VPS deploys family proxy infrastructure in under 10 minutes.
---
