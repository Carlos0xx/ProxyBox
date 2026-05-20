"""Unit tests for subscription URI builders (pure functions, no DB / no FS)."""

import base64

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.services.subscriptions import (
    build_hysteria2_uri,
    build_vless_uri,
    derive_reality_public_key,
)


def _gen_keypair() -> tuple[str, str]:
    priv = X25519PrivateKey.generate()
    priv_b = priv.private_bytes_raw()
    pub_b = priv.public_key().public_bytes_raw()
    return (
        base64.urlsafe_b64encode(priv_b).rstrip(b"=").decode(),
        base64.urlsafe_b64encode(pub_b).rstrip(b"=").decode(),
    )


def test_derive_reality_public_key_matches_keypair():
    priv_b64, expected_pub_b64 = _gen_keypair()
    assert derive_reality_public_key(priv_b64) == expected_pub_b64


def test_derive_is_deterministic():
    priv_b64, _ = _gen_keypair()
    a = derive_reality_public_key(priv_b64)
    b = derive_reality_public_key(priv_b64)
    assert a == b


def _fake_sb_cfg(priv_b64: str) -> dict:
    return {
        "inbounds": [
            {
                "type": "vless",
                "tag": "vless-template",
                "users": [{"flow": "xtls-rprx-vision"}],
                "tls": {
                    "server_name": "www.example.com",
                    "reality": {
                        "private_key": priv_b64,
                        "short_id": ["abc123def4567890"],
                    },
                },
            },
            {
                "type": "hysteria2",
                "tag": "hy2-template",
                "obfs": {"password": "obfs-pw-hex"},
                "tls": {"server_name": "www.example.com"},
            },
        ]
    }


def test_build_vless_uri_shape():
    priv_b64, pub_b64 = _gen_keypair()
    device = {
        "name": "test-phone",
        "vless_uuid": "00000000-0000-0000-0000-000000000001",
        "vless_port": 11001,
    }
    uri = build_vless_uri(device, _fake_sb_cfg(priv_b64), "1.2.3.4")
    assert uri.startswith(
        "vless://00000000-0000-0000-0000-000000000001@1.2.3.4:11001?"
    )
    assert "security=reality" in uri
    assert "sni=www.example.com" in uri
    assert f"pbk={pub_b64}" in uri
    assert "sid=abc123def4567890" in uri
    assert "flow=xtls-rprx-vision" in uri
    assert uri.endswith("#ProxyBox-test-phone-vless")


def test_build_hysteria2_uri_shape():
    priv_b64, _ = _gen_keypair()
    device = {
        "name": "test-phone",
        "hy2_password": "fake-hy2-pw",
        "hy2_port": 21001,
    }
    uri = build_hysteria2_uri(device, _fake_sb_cfg(priv_b64), "1.2.3.4")
    assert uri.startswith("hysteria2://fake-hy2-pw@1.2.3.4:21001?")
    assert "sni=www.example.com" in uri
    assert "obfs=salamander" in uri
    assert "obfs-password=obfs-pw-hex" in uri
    assert "insecure=1" in uri
    assert uri.endswith("#ProxyBox-test-phone-hy2")
