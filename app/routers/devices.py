"""Device CRUD endpoints (currently read-only list; create/update/delete TBD)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.token import admin_auth
from app.db.connection import connection
from app.models.device import Device

router = APIRouter(
    prefix="/admin/{token}/api/devices",
    dependencies=[Depends(admin_auth)],
    tags=["devices"],
)

_LIST_SQL = """
SELECT name, label, kind, vless_uuid, hy2_password,
       vless_port, hy2_port, sni,
       created_at, last_seen, last_ip,
       revoked, notes, sub_token, paused_until
FROM device
ORDER BY revoked, created_at DESC
"""


@router.get("/list")
async def list_devices() -> dict[str, list[Device]]:
    with connection() as conn:
        rows = conn.execute(_LIST_SQL).fetchall()
    return {"devices": [Device.model_validate(dict(r)) for r in rows]}
