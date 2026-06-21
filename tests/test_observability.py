"""
Tests for observability components.
"""

from __future__ import annotations

import time

import pytest

from observability.metrics import Counter, Gauge, Histogram, MetricsCollector
from observability.tracer import AgentTracer, Span, TraceContext


class TestSpan:
    """Tests for the Span dataclass."""

    def test_creation(self):
        span = Span(name="test_span", trace_id="trace-1")
        assert span.name == "test_span"
        assert span.trace_id == "trace-1"
        assert span.status == "running"
        assert span.end_time is None

    def test_finish_success(self):
        span = Span(name="span", trace_id="t1")
        span.finish()
        assert span.status == "success"
        assert span.end_time is not None
        assert span.duration_ms >= 0

    def test_finish_with_error(self):
        span = Span(name="span", trace_id="t1")
        span.finish(error="something went wrong")
        assert span.status == "error"
        assert span.error == "something went wrong"

    def test_add_event(self):
        span = Span(name="span")
        span.add_event("checkpoint", {"step": 1})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "checkpoint"

    def test_set_attribute(self):
        span = Span(name="span")
        span.set_attribute("agent_name", "PlannerAgent")
        assert span.attributes["agent_name"] == "PlannerAgent"

    def test_to_dict(self):
        span = Span(name="span", trace_id="t1")
        span.finish()
        d = span.to_dict()
        assert "span_id" in d
        assert "trace_id" in d
        assert "duration_ms" in d
        assert "status" in d


class TestTraceContext:
    """Tests for the TraceContext dataclass."""

    def test_creation(self):
        trace = TraceContext()
        assert trace.trace_id is not None
        assert trace.spans == []

    def test_add_span(self):
        trace = TraceContext()
        span = Span(name="span", trace_id=trace.trace_id)
        trace.add_span(span)
        assert len(trace.spans) == 1

    def test_total_duration(self):
        trace = TraceContext()
        time.sleep(0.01)
        assert trace.total_duration_ms >= 0

    def test_has_errors_false_when_clean(self):
        trace = TraceContext()
        span = Span(name="span")
        span.finish()
        trace.add_span(span)
        assert trace.has_errors is False

    def test_has_errors_true_when_error(self):
        trace = TraceContext()
        span = Span(name="span")
        span.finish(error="boom")
        trace.add_span(span)
        assert trace.has_errors is True

    def test_to_dict(self):
        trace = TraceContext()
        d = trace.to_dict()
        assert "trace_id" in d
        assert "spans" in d


class TestAgentTracer:
    """Tests for AgentTracer."""

    @pytest.fixture
    def tracer(self):
        return AgentTracer(enabled=True)

    def test_start_trace(self, tracer):
        trace = tracer.start_trace("test_trace")
        assert trace.trace_id in tracer._active_traces

    def test_end_trace(self, tracer):
        trace = tracer.start_trace("test_trace")
        ended = tracer.end_trace(trace.trace_id)
        assert ended is not None
        assert trace.trace_id not in tracer._active_traces
        assert len(tracer._completed_traces) == 1

    def test_span_context_manager_success(self, tracer):
        trace = tracer.start_trace("test")
        with tracer.span("my_span", trace_id=trace.trace_id) as span:
            span.set_attribute("key", "value")
        assert span.status == "success"
        assert span.end_time is not None

    def test_span_context_manager_error(self, tracer):
        trace = tracer.start_trace("test")
        with pytest.raises(ValueError):
            with tracer.span("failing_span", trace_id=trace.trace_id) as span:
                raise ValueError("test error")
        assert span.status == "error"
        assert span.error == "test error"

    def test_disabled_tracer(self):
        tracer = AgentTracer(enabled=False)
        with tracer.span("span") as span:
            assert span.name == "span"

    def test_get_recent_traces(self, tracer):
        for i in range(3):
            trace = tracer.start_trace(f"trace_{i}")
            tracer.end_trace(trace.trace_id)
        recent = tracer.get_recent_traces(limit=2)
        assert len(recent) == 2

    def test_metrics_summary(self, tracer):
        trace = tracer.start_trace("test")
        with tracer.span("span", trace_id=trace.trace_id):
            pass
        tracer.end_trace(trace.trace_id)
        summary = tracer.get_metrics_summary()
        assert summary["total_traces"] == 1
        assert summary["total_spans"] >= 1


class TestCounter:
    """Tests for Counter metric."""

    def test_initial_value_zero(self):
        c = Counter(name="test")
        assert c.value == 0.0

    def test_increment(self):
        c = Counter(name="test")
        c.increment()
        assert c.value == 1.0

    def test_increment_custom_amount(self):
        c = Counter(name="test")
        c.increment(5.0)
        assert c.value == 5.0


class TestGauge:
    """Tests for Gauge metric."""

    def test_set(self):
        g = Gauge(name="test")
        g.set(42.0)
        assert g.value == 42.0

    def test_increment_decrement(self):
        g = Gauge(name="test")
        g.increment(3)
        g.decrement(1)
        assert g.value == 2.0


class TestHistogram:
    """Tests for Histogram metric."""

    def test_initial_empty(self):
        h = Histogram(name="test")
        assert h.count == 0
        assert h.mean == 0.0

    def test_observe(self):
        h = Histogram(name="test")
        h.observe(10.0)
        h.observe(20.0)
        assert h.count == 2
        assert h.mean == 15.0
        assert h.min == 10.0
        assert h.max == 20.0

    def test_percentile(self):
        h = Histogram(name="test")
        for i in range(1, 101):
            h.observe(float(i))
        p50 = h.percentile(50)
        assert 45 <= p50 <= 55

    def test_empty_percentile(self):
        h = Histogram(name="test")
        assert h.percentile(50) == 0.0


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    @pytest.fixture
    def collector(self):
        return MetricsCollector(enabled=True)

    def test_initialization(self, collector):
        assert collector.enabled is True

    def test_record_agent_run_success(self, collector):
        collector.record_agent_run("PlannerAgent", 100.0, success=True, tokens=500)
        summary = collector.get_summary()
        assert summary["counters"]["agent_runs_total"] == 1
        assert summary["counters"]["agent_runs_success"] == 1
        assert summary["counters"]["tokens_used_total"] == 500

    def test_record_agent_run_failure(self, collector):
        collector.record_agent_run("CodingAgent", 200.0, success=False)
        summary = collector.get_summary()
        assert summary["counters"]["agent_runs_failed"] == 1

    def test_record_tool_call(self, collector):
        collector.record_tool_call("web_search", 50.0, success=True)
        summary = collector.get_summary()
        assert summary["counters"]["tool_calls_total"] == 1

    def test_record_workflow_run(self, collector):
        collector.record_workflow_run("sequential", 300.0, success=True)
        summary = collector.get_summary()
        assert summary["counters"]["workflow_runs_total"] == 1

    def test_get_summary(self, collector):
        summary = collector.get_summary()
        assert "counters" in summary
        assert "gauges" in summary
        assert "histograms" in summary
        assert "uptime_seconds" in summary

    def test_prometheus_export(self, collector):
        collector.increment("test_counter")
        output = collector.export_prometheus()
        assert "test_counter" in output
        assert "1.0" in output

    def test_disabled_collector(self):
        collector = MetricsCollector(enabled=False)
        collector.record_agent_run("test", 100.0, success=True)
        summary = collector.get_summary()
        assert summary["counters"]["agent_runs_total"] == 0

    def test_set_gauge(self, collector):
        collector.set_gauge("active_agents", 3.0)
        summary = collector.get_summary()
        assert summary["gauges"]["active_agents"] == 3.0
