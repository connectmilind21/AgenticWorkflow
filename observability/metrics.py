"""
Metrics collection for the Agentic Workflow Framework.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Counter:
    """A simple monotonically increasing counter."""

    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)

    def increment(self, amount: float = 1.0) -> None:
        self.value += amount


@dataclass
class Gauge:
    """A gauge that can go up and down."""

    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        self.value = value

    def increment(self, amount: float = 1.0) -> None:
        self.value += amount

    def decrement(self, amount: float = 1.0) -> None:
        self.value -= amount


@dataclass
class Histogram:
    """Tracks distribution of values (latency, token counts, etc.)."""

    name: str
    observations: list[float] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)

    def observe(self, value: float) -> None:
        self.observations.append(value)

    @property
    def count(self) -> int:
        return len(self.observations)

    @property
    def sum(self) -> float:
        return sum(self.observations)

    @property
    def mean(self) -> float:
        return self.sum / self.count if self.count else 0.0

    @property
    def max(self) -> float:
        return max(self.observations) if self.observations else 0.0

    @property
    def min(self) -> float:
        return min(self.observations) if self.observations else 0.0

    def percentile(self, p: float) -> float:
        """Calculate the p-th percentile."""
        if not self.observations:
            return 0.0
        sorted_obs = sorted(self.observations)
        idx = int(p / 100 * len(sorted_obs))
        return sorted_obs[min(idx, len(sorted_obs) - 1)]


class MetricsCollector:
    """
    Collects and exposes metrics for agents and workflows.

    Tracks:
    - Agent run counts and latencies
    - Tool invocations
    - Token usage
    - Workflow success/failure rates
    - Cost estimates
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._start_time = time.time()

        # Pre-register common metrics
        self._init_default_metrics()

    def _init_default_metrics(self) -> None:
        """Initialize default metrics."""
        default_counters = [
            "agent_runs_total",
            "agent_runs_success",
            "agent_runs_failed",
            "tool_calls_total",
            "workflow_runs_total",
            "tokens_used_total",
        ]
        for name in default_counters:
            self._counters[name] = Counter(name=name)

        default_histograms = [
            "agent_run_duration_ms",
            "tool_call_duration_ms",
            "workflow_duration_ms",
            "tokens_per_run",
        ]
        for name in default_histograms:
            self._histograms[name] = Histogram(name=name)

        self._gauges["active_agents"] = Gauge(name="active_agents")
        self._gauges["active_workflows"] = Gauge(name="active_workflows")

    def record_agent_run(
        self,
        agent_name: str,
        duration_ms: float,
        success: bool,
        tokens: int = 0,
    ) -> None:
        """Record an agent run."""
        if not self.enabled:
            return
        self.increment("agent_runs_total")
        if success:
            self.increment("agent_runs_success")
        else:
            self.increment("agent_runs_failed")

        self.observe("agent_run_duration_ms", duration_ms)
        if tokens:
            self.increment("tokens_used_total", tokens)
            self.observe("tokens_per_run", tokens)

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record a tool call."""
        if not self.enabled:
            return
        self.increment("tool_calls_total")
        self.observe("tool_call_duration_ms", duration_ms)

    def record_workflow_run(
        self,
        workflow_name: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record a workflow execution."""
        if not self.enabled:
            return
        self.increment("workflow_runs_total")
        self.observe("workflow_duration_ms", duration_ms)

    def increment(self, name: str, amount: float = 1.0) -> None:
        """Increment a counter."""
        if name not in self._counters:
            self._counters[name] = Counter(name=name)
        self._counters[name].increment(amount)

    def observe(self, name: str, value: float) -> None:
        """Record a histogram observation."""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name=name)
        self._histograms[name].observe(value)

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        if name not in self._gauges:
            self._gauges[name] = Gauge(name=name)
        self._gauges[name].set(value)

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of all collected metrics."""
        uptime = time.time() - self._start_time

        counters = {name: c.value for name, c in self._counters.items()}
        gauges = {name: g.value for name, g in self._gauges.items()}
        histograms = {
            name: {
                "count": h.count,
                "sum": h.sum,
                "mean": h.mean,
                "min": h.min,
                "max": h.max,
                "p50": h.percentile(50),
                "p95": h.percentile(95),
                "p99": h.percentile(99),
            }
            for name, h in self._histograms.items()
            if h.count > 0
        }

        return {
            "uptime_seconds": uptime,
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
        }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines: list[str] = []
        for name, counter in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {counter.value}")
        for name, gauge in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {gauge.value}")
        for name, hist in self._histograms.items():
            if hist.count > 0:
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count {hist.count}")
                lines.append(f"{name}_sum {hist.sum}")
        return "\n".join(lines) + "\n"
