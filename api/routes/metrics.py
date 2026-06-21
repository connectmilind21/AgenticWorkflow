"""
Metrics API routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

_metrics_collector = None


def _get_metrics() -> Any:
    """Lazily get/create the metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        from observability.metrics import MetricsCollector

        _metrics_collector = MetricsCollector()
    return _metrics_collector


@router.get("/", summary="Get metrics summary")
async def get_metrics() -> dict[str, Any]:
    """Return current metrics summary."""
    return _get_metrics().get_summary()


@router.get("/prometheus", summary="Prometheus metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics() -> str:
    """Return metrics in Prometheus text format."""
    return _get_metrics().export_prometheus()
