"""System status endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.auth.token import admin_auth
from app.config import get_settings
from app.services import system_stats

router = APIRouter(
    prefix="/admin/{token}/api",
    dependencies=[Depends(admin_auth)],
    tags=["system"],
)


@router.get("/status")
async def status() -> dict:
    settings = get_settings()
    return {
        "services": {
            unit: system_stats.systemctl_is_active(unit)
            for unit in settings.services.monitored
        },
        "load": system_stats.loadavg(),
        "uptime": system_stats.uptime_pretty(),
        "mem": system_stats.mem_stats(),
        "disk": system_stats.disk_stats(),
        "cpu_pct": system_stats.cpu_pct(),
        "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": system_stats.hostname(),
    }
