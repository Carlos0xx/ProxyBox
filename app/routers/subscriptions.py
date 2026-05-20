"""Public subscription endpoint — sub_token IS the auth, no admin token required.

Clients (Shadowrocket, sing-box, Hiddify, ...) fetch the URI list via HTTP GET.
The path validator constrains sub_token to hex/base64-safe chars so the URL
can never be tricked into traversing the filesystem.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import PlainTextResponse

from app.services import subscriptions

router = APIRouter(prefix="/api/sub", tags=["subscriptions"])

SubTokenInPath = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{8,64}$")]


@router.get("/{sub_token}", response_class=PlainTextResponse)
async def get_subscription(sub_token: SubTokenInPath) -> str:
    content = subscriptions.read_subscription(sub_token)
    if content is None:
        raise HTTPException(404, "subscription not found")
    return content
