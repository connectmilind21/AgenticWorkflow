"""
Agent tracing for observability in the Agentic Workflow Framework.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Span:
    """Represents a single traced operation."""

    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str = ""
    parent_id: str | None = None
    name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: float = 0.0
    status: str = "running"
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def finish(self, error: str | None = None) -> None:
        """Mark the span as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.error = error
        self.status = "error" if error else "success"

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        """Add a timestamped event to the span."""
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Serialize span to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
            "error": self.error,
        }


@dataclass
class TraceContext:
    """Holds all spans for a complete trace."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spans: list[Span] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def add_span(self, span: Span) -> None:
        self.spans.append(span)

    @property
    def total_duration_ms(self) -> float:
        if not self.spans:
            return 0.0
        return (time.time() - self.start_time) * 1000

    @property
    def has_errors(self) -> bool:
        return any(s.error for s in self.spans)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "total_duration_ms": self.total_duration_ms,
            "has_errors": self.has_errors,
            "span_count": len(self.spans),
            "spans": [s.to_dict() for s in self.spans],
        }


class AgentTracer:
    """
    Traces agent and workflow execution for observability.

    Records spans for each agent run, workflow step, and tool call.
    Traces can be exported to various backends.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._active_traces: dict[str, TraceContext] = {}
        self._completed_traces: list[TraceContext] = []
        self._logger = logger.bind(component="tracer")

    def start_trace(self, name: str) -> TraceContext:
        """Start a new trace context."""
        trace = TraceContext()
        self._active_traces[trace.trace_id] = trace
        self._logger.debug("Trace started", trace_id=trace.trace_id, name=name)
        return trace

    def end_trace(self, trace_id: str) -> TraceContext | None:
        """End and archive a trace."""
        trace = self._active_traces.pop(trace_id, None)
        if trace:
            self._completed_traces.append(trace)
            self._logger.debug(
                "Trace ended",
                trace_id=trace_id,
                spans=len(trace.spans),
                duration_ms=trace.total_duration_ms,
            )
        return trace

    @contextmanager
    def span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """Context manager that creates and tracks a span."""
        if not self.enabled:
            dummy = Span(name=name)
            yield dummy
            return

        s = Span(
            name=name,
            trace_id=trace_id or "",
            parent_id=parent_id,
            attributes=attributes or {},
        )

        if trace_id and trace_id in self._active_traces:
            self._active_traces[trace_id].add_span(s)

        try:
            yield s
        except Exception as exc:
            s.finish(error=str(exc))
            raise
        else:
            s.finish()

    def get_recent_traces(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most recent completed traces."""
        recent = self._completed_traces[-limit:]
        return [t.to_dict() for t in reversed(recent)]

    def get_metrics_summary(self) -> dict[str, Any]:
        """Return aggregated metrics from all traces."""
        all_spans = [
            span
            for trace in self._completed_traces
            for span in trace.spans
        ]
        if not all_spans:
            return {"total_traces": 0, "total_spans": 0}

        durations = [s.duration_ms for s in all_spans if s.end_time]
        errors = [s for s in all_spans if s.error]

        return {
            "total_traces": len(self._completed_traces),
            "total_spans": len(all_spans),
            "error_count": len(errors),
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
        }
