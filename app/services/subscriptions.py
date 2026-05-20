"""Subscription generation: URI builders + file IO.

A subscription is a plain-text file containing one URI per line that a
sing-box-compatible client (Shadowrocket, sing-box mobile, Hiddify, etc.)
can fetch via HTTP and decode into a node list. Files live at
``settings.paths.sub_dir / {sub_token}.txt`` — the sub_token IS the
authentication, so leaking it leaks the device. Rotate with
``POST /api/devices/{name}/regen-subs``.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import yaml
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.config import get_settings
from app.services import singbox


def derive_reality_public_key(private_b64: str) -> str:
    """Derive Reality X25519 public key (base64url, no padding) from private."""
    priv_bytes = base64.urlsafe_b64decode(private_b64 + "==")
    priv = X25519PrivateKey.from_private_bytes(priv_bytes)
    pub_bytes = priv.public_key().public_bytes_raw()
    return base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()


def build_vless_uri(device: dict[str, Any], sb_cfg: dict[str, Any], vps_host: str) -> str:
    vless_tpl = singbox.find_template_inbound(sb_cfg, "vless")
    reality = vless_tpl["tls"]["reality"]
    sni = vless_tpl["tls"]["server_name"]
    public_b64 = derive_reality_public_key(reality["private_key"])
    short_id = reality["short_id"][0]
    tpl_users = vless_tpl.get("users") or []
    flow = (tpl_users[0].get("flow") if tpl_users else None) or "xtls-rprx-vision"

    return (
        f"vless://{device['vless_uuid']}@{vps_host}:{device['vless_port']}"
        f"?security=reality&sni={sni}&fp=chrome&pbk={public_b64}&sid={short_id}"
        f"&type=tcp&flow={flow}"
        f"#ProxyBox-{device['name']}-vless"
    )


def build_hysteria2_uri(device: dict[str, Any], sb_cfg: dict[str, Any], vps_host: str) -> str:
    hy2_tpl = singbox.find_template_inbound(sb_cfg, "hysteria2")
    obfs_pw = hy2_tpl.get("obfs", {}).get("password", "")
    sni = (
        hy2_tpl.get("tls", {}).get("server_name")
        or singbox.find_template_inbound(sb_cfg, "vless")["tls"]["server_name"]
    )

    return (
        f"hysteria2://{device['hy2_password']}@{vps_host}:{device['hy2_port']}"
        f"?sni={sni}&obfs=salamander&obfs-password={obfs_pw}&insecure=1"
        f"#ProxyBox-{device['name']}-hy2"
    )


def _reality_params(sb_cfg: dict[str, Any]) -> dict[str, Any]:
    """Pull the bits both Clash and Surge clients need from the sing-box config."""
    vless_tpl = singbox.find_template_inbound(sb_cfg, "vless")
    reality = vless_tpl["tls"]["reality"]
    tpl_users = vless_tpl.get("users") or []
    return {
        "sni": vless_tpl["tls"]["server_name"],
        "public_b64": derive_reality_public_key(reality["private_key"]),
        "short_id": reality["short_id"][0],
        "flow": (tpl_users[0].get("flow") if tpl_users else None) or "xtls-rprx-vision",
    }


def _hy2_obfs_password(sb_cfg: dict[str, Any]) -> str:
    return singbox.find_template_inbound(sb_cfg, "hysteria2").get("obfs", {}).get("password", "")


def _require_public_host() -> str:
    vps_host = get_settings().server.public_host
    if not vps_host:
        raise RuntimeError(
            "server.public_host is empty in config.yaml — set it before generating subs"
        )
    return vps_host


def build_clash_yaml(
    device: dict[str, Any],
    sb_cfg: dict[str, Any] | None = None,
    *,
    with_tun: bool = False,
) -> str:
    """Mihomo / Clash for iOS / Stash / Clash Verge YAML config.

    Single-proxy + select group + GeoIP-CN-direct rules. ``with_tun=True``
    enables transparent routing for AsusWRT-Merlin (clash-tun on the router).
    """
    if sb_cfg is None:
        sb_cfg = singbox.read_config()
    vps_host = _require_public_host()
    r = _reality_params(sb_cfg)
    name_v = f"ProxyBox-{device['name']}-vless"
    name_h = f"ProxyBox-{device['name']}-hy2"
    cfg: dict[str, Any] = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "proxies": [
            {
                "name": name_v,
                "type": "vless",
                "server": vps_host,
                "port": device["vless_port"],
                "uuid": device["vless_uuid"],
                "network": "tcp",
                "udp": True,
                "tls": True,
                "flow": r["flow"],
                "servername": r["sni"],
                "reality-opts": {"public-key": r["public_b64"], "short-id": r["short_id"]},
                "client-fingerprint": "chrome",
            },
            {
                "name": name_h,
                "type": "hysteria2",
                "server": vps_host,
                "port": device["hy2_port"],
                "password": device["hy2_password"],
                "sni": r["sni"],
                "obfs": "salamander",
                "obfs-password": _hy2_obfs_password(sb_cfg),
                "skip-cert-verify": True,
            },
        ],
        "proxy-groups": [
            {"name": "PROXY", "type": "select", "proxies": [name_v, name_h, "DIRECT"]},
            {
                "name": "AUTO",
                "type": "url-test",
                "proxies": [name_v, name_h],
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
            },
        ],
        "rules": ["GEOIP,LAN,DIRECT", "GEOIP,CN,DIRECT", "MATCH,PROXY"],
    }
    if with_tun:
        cfg["tun"] = {
            "enable": True,
            "stack": "system",
            "dns-hijack": ["any:53"],
            "auto-route": True,
            "auto-detect-interface": True,
        }
    return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)


def build_shadowrocket_conf(
    device: dict[str, Any], sb_cfg: dict[str, Any] | None = None
) -> str:
    """Shadowrocket / Surge .conf format. VLESS Reality syntax is Shadowrocket-specific."""
    if sb_cfg is None:
        sb_cfg = singbox.read_config()
    vps_host = _require_public_host()
    r = _reality_params(sb_cfg)
    name_v = f"ProxyBox-{device['name']}-vless"
    name_h = f"ProxyBox-{device['name']}-hy2"
    obfs_pw = _hy2_obfs_password(sb_cfg)
    # Surge .conf wants each proxy on a single physical line — build the
    # two long lines piecewise so the literal string in the file stays
    # readable and ruff E501 stays happy.
    vless_parts = [
        f"{name_v} = vless, {vps_host}, {device['vless_port']}",
        f"username={device['vless_uuid']}",
        "tls=true",
        f"sni={r['sni']}",
        f"flow={r['flow']}",
        f"reality-pbk={r['public_b64']}",
        f"reality-sid={r['short_id']}",
        "fp=chrome",
    ]
    hy2_parts = [
        f"{name_h} = hysteria2, {vps_host}, {device['hy2_port']}",
        f"password={device['hy2_password']}",
        f"sni={r['sni']}",
        "obfs=salamander",
        f"obfs-password={obfs_pw}",
        "skip-cert-verify=true",
    ]
    vless_line = ", ".join(vless_parts)
    hy2_line = ", ".join(hy2_parts)
    return f"""[General]
bypass-system = true
skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, localhost, *.local
dns-server = system

[Proxy]
{vless_line}
{hy2_line}

[Proxy Group]
PROXY = select, {name_v}, {name_h}, DIRECT

[Rule]
GEOIP,CN,DIRECT
FINAL,PROXY
"""


def generate_subscription_text(device: dict[str, Any], sb_cfg: dict[str, Any] | None = None) -> str:
    """Build the subscription file content for one device.

    Raises RuntimeError if server.public_host is not configured — the URIs
    need a host clients can connect to.
    """
    if sb_cfg is None:
        sb_cfg = singbox.read_config()
    vps_host = get_settings().server.public_host
    if not vps_host:
        raise RuntimeError(
            "server.public_host is empty in config.yaml — set it before generating subs"
        )
    return (
        build_vless_uri(device, sb_cfg, vps_host)
        + "\n"
        + build_hysteria2_uri(device, sb_cfg, vps_host)
        + "\n"
    )


def _sub_path(sub_token: str) -> Path:
    return Path(get_settings().paths.sub_dir) / f"{sub_token}.txt"


def write_subscription_file(device: dict[str, Any], sb_cfg: dict[str, Any] | None = None) -> Path:
    sub_dir = Path(get_settings().paths.sub_dir)
    sub_dir.mkdir(parents=True, exist_ok=True)
    content = generate_subscription_text(device, sb_cfg)
    path = _sub_path(device["sub_token"])
    path.write_text(content)
    path.chmod(0o644)
    return path


def read_subscription(sub_token: str) -> str | None:
    path = _sub_path(sub_token)
    if not path.exists():
        return None
    return path.read_text()


def delete_subscription_file(sub_token: str) -> bool:
    path = _sub_path(sub_token)
    if path.exists():
        path.unlink()
        return True
    return False
