# Subscription URLs

When you `POST /api/devices/new`, ProxyBox returns a `subscription_url_path`
like `/api/sub/{sub_token}`. The full URL clients hit is:

```
http://<server.public_host>:<admin.port>/api/sub/{sub_token}
```

(or `https://` if you've put Caddy / nginx in front of port 8080)

## Content

Plain text, one URI per line, both protocols:

```
vless://{uuid}@{host}:{vless_port}?security=reality&sni={sni}&fp=chrome&pbk={pubkey}&sid={short_id}&type=tcp&flow=xtls-rprx-vision#ProxyBox-{name}-vless
hysteria2://{password}@{host}:{hy2_port}?sni={sni}&obfs=salamander&obfs-password={obfs_pw}&insecure=1#ProxyBox-{name}-hy2
```

## Client compatibility

| Client | Subscription import |
|---|---|
| Shadowrocket (iOS) | "Type: Subscribe", paste URL |
| sing-box (iOS / Android) | "+ → Subscribe", paste URL |
| Hiddify Next (desktop) | "+ → Add profile from URL" |
| NekoBox (Android) | "+ → Subscription" |
| v2rayN (Windows) | "Subscriptions → Add", paste URL |

Some clients can also parse a single `vless://` URI directly — for those,
copy just one line of the subscription output. **Shadowrocket prefers
subscriptions over direct URI paste** (confirmed in our testing).

## Rotation

If a device's `sub_token` is leaked:

```bash
curl -X POST http://<host>:8080/admin/<admin_token>/api/devices/<name>/regen-subs
```

The old sub_token immediately returns 404. The new URL has the same device
config (same UUID, same ports) — clients re-import once.
