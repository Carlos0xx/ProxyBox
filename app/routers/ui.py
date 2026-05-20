"""Serve the single-file SPA dashboard.

GET /admin/{token}/ returns the HTML with ``{{TOKEN}}`` replaced by the
URL-path token so the embedded JS can call ``/admin/{token}/api/...``
without any second auth handshake.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import HTMLResponse

from app.auth.token import admin_auth
from app.config import get_settings

router = APIRouter(
    prefix="/admin/{token}",
    dependencies=[Depends(admin_auth)],
    tags=["ui"],
)

_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def index(token: Annotated[str, Path()]) -> HTMLResponse:
    spa = get_settings().paths.static_dir / "index.html"
    if not spa.exists():
        raise HTTPException(
            500, f"SPA not found at {spa} — ship static/ directory or set paths.static_dir"
        )
    body = spa.read_text(encoding="utf-8").replace("{{TOKEN}}", token)
    return HTMLResponse(content=body, headers=_NO_CACHE_HEADERS)
