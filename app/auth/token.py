"""URL-path admin token authentication.

Mounted as a FastAPI dependency on routers prefixed with /admin/{token}/.
Uses constant-time comparison to avoid timing leaks.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import HTTPException, Path

from app.config import get_settings


async def admin_auth(token: Annotated[str, Path()]) -> str:
    expected = get_settings().admin.token
    if not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Unauthorized")
    return token
