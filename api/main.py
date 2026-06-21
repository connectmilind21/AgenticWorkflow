"""
FastAPI application for the Agentic Workflow Framework.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentic_workflow.config import get_settings
from api.routes import agents, health, metrics, workflows

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    settings = get_settings()
    logger.info(
        "Starting Agentic Workflow API",
        version=settings.app_version,
        environment=settings.environment,
    )
    yield
    logger.info("Shutting down Agentic Workflow API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A modular, scalable, production-ready Agentic AI framework API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
    app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):  # type: ignore[no-untyped-def]
        logger.exception("Unhandled exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    return app


app = create_app()
