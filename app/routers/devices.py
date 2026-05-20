"""Device endpoints: list, single read, label / notes update. Create / delete TBD."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from app.auth.token import admin_auth
from app.db.connection import connection
from app.models.device import Device

router = APIRouter(
    prefix="/admin/{token}/api/devices",
    dependencies=[Depends(admin_auth)],
    tags=["devices"],
)

NameInPath = Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{3,32}$")]


class LabelUpdate(BaseModel):
    label: str = Field(default="", max_length=64)


class NotesUpdate(BaseModel):
    notes: str = Field(default="", max_length=1024)


_COLUMNS = (
    "name, label, kind, vless_uuid, hy2_password, "
    "vless_port, hy2_port, sni, "
    "created_at, last_seen, last_ip, "
    "revoked, notes, sub_token, paused_until"
)

_LIST_SQL = f"SELECT {_COLUMNS} FROM device ORDER BY revoked, created_at DESC"
_GET_SQL = f"SELECT {_COLUMNS} FROM device WHERE name = ?"


@router.get("/list")
async def list_devices() -> dict[str, list[Device]]:
    with connection() as conn:
        rows = conn.execute(_LIST_SQL).fetchall()
    return {"devices": [Device.model_validate(dict(r)) for r in rows]}


@router.get("/{name}")
async def get_device(name: NameInPath) -> Device:
    with connection() as conn:
        row = conn.execute(_GET_SQL, (name,)).fetchone()
    if row is None:
        raise HTTPException(404, "device not found")
    return Device.model_validate(dict(row))


@router.post("/{name}/label")
async def update_label(name: NameInPath, body: LabelUpdate) -> dict[str, str]:
    with connection() as conn:
        cur = conn.execute(
            "UPDATE device SET label = ? WHERE name = ?", (body.label, name)
        )
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "device not found")
    return {"name": name, "label": body.label}


@router.post("/{name}/notes")
async def update_notes(name: NameInPath, body: NotesUpdate) -> dict[str, str]:
    with connection() as conn:
        cur = conn.execute(
            "UPDATE device SET notes = ? WHERE name = ?", (body.notes, name)
        )
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "device not found")
    return {"name": name, "notes": body.notes}
