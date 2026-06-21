"""
Health check routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Health check")
async def health_check() -> dict[str, Any]:
    """Return service health status."""
    return {
        "status": "healthy",
        "service": "agentic-workflow",
    }


@router.get("/ready", summary="Readiness probe")
async def readiness() -> dict[str, Any]:
    """Return service readiness status."""
    return {"status": "ready"}


@router.get("/live", summary="Liveness probe")
async def liveness() -> dict[str, Any]:
    """Return service liveness status."""
    return {"status": "alive"}
