"""ProxyBox FastAPI application entry point.

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import system


def create_app() -> FastAPI:
    app = FastAPI(title="ProxyBox", version="0.1.0")
    app.include_router(system.router)
    return app


app = create_app()
