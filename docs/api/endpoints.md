# API endpoints

All endpoints (except `/api/sub/{token}`) sit under `/admin/{token}/`
where `{token}` is the value of `admin.token` in `/etc/proxybox/config.yaml`.

## System

- `GET  /api/status` — service / load / mem / disk / cpu / hostname
- `GET  /api/logs/{name}?n=50` — journalctl wrapper (allowlisted by `services.monitored`)

## Devices

- `GET  /api/devices` — per-device current usage (today + 24h + last_seen)
- `GET  /api/devices/list` — raw device config rows (incl. revoked)
- `GET  /api/devices/{name}` — single device detail
- `POST /api/devices/new` — create device (allocates ports, generates UUID + sub_token, writes sing-box config + sub file)
- `POST /api/devices/{name}/label` — update label
- `POST /api/devices/{name}/notes` — update notes
- `POST /api/devices/{name}/pause` — body `{until_ts: int}` (0 = indefinite)
- `POST /api/devices/{name}/resume`
- `POST /api/devices/{name}/revoke` — soft delete (DB row kept, inbounds + sub file gone)
- `POST /api/devices/{name}/delete` — hard delete
- `POST /api/devices/{name}/rename` — body `{new_name: str}`
- `POST /api/devices/{name}/regen-subs` — rotate sub_token + URL

## Subscriptions (public)

- `GET /api/sub/{sub_token}` — text/plain list of `vless://` + `hysteria2://` URIs. The `sub_token` itself is the secret.

## Traffic

- `GET /api/traffic` — 24h totals + per-hour breakdown
- `GET /api/history/devices?days=N` — per-device daily totals
- `GET /api/history/device/{name}?days=N` — single device hourly
- `GET /api/history/all-daily?days=N` — system daily totals
- `GET /api/history/export?days=N&format=csv` — CSV dump

## Bans

- `GET  /api/bans` — current fail2ban [manual] jail status
- `POST /action/block` — body `{ip: str}`
- `POST /action/unblock` — body `{ip: str}`

## Admin actions

- `POST /action/restart/{svc}` — systemctl restart (allowlisted by `services.monitored`)
- `POST /action/rotate` — body `{confirm: true}` — rotate Reality keypair + rewrite all sub files
- `POST /api/auth/rotate-admin-token` — invalidate current URL prefix, return a new one

## Passkey (opt-in, `features.passkey: true`)

- `POST /auth/webauthn/login/begin` (public)
- `POST /auth/webauthn/login/complete` (public — returns session cookie)
- `POST /auth/webauthn/logout`
- `POST /admin/{token}/api/auth/webauthn/register/begin` (admin token OR session)
- `POST /admin/{token}/api/auth/webauthn/register/complete`
- `GET  /admin/{token}/api/auth/passkeys` — list registered
- `DELETE /admin/{token}/api/auth/passkeys/{cid}` — revoke
