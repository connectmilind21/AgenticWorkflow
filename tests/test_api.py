"""
Tests for FastAPI routes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthRoutes:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness(self, client):
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_liveness(self, client):
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestAgentRoutes:
    """Tests for agent API endpoints."""

    def test_list_agents(self, client):
        response = client.get("/api/v1/agents/")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) > 0

    def test_get_agent_info(self, client):
        response = client.get("/api/v1/agents/planner")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "planner"

    def test_get_unknown_agent_returns_404(self, client):
        response = client.get("/api/v1/agents/nonexistent")
        assert response.status_code == 404

    def test_run_planner_agent(self, client):
        response = client.post(
            "/api/v1/agents/run",
            json={"agent_type": "planner", "task": "Plan a research project"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["agent_name"] == "PlannerAgent"

    def test_run_unknown_agent_returns_404(self, client):
        response = client.post(
            "/api/v1/agents/run",
            json={"agent_type": "nonexistent", "task": "task"},
        )
        assert response.status_code == 404

    def test_run_agent_with_context(self, client):
        response = client.post(
            "/api/v1/agents/run",
            json={
                "agent_type": "researcher",
                "task": "Research AI trends",
                "context": {"depth": "comprehensive"},
            },
        )
        assert response.status_code == 200


class TestWorkflowRoutes:
    """Tests for workflow API endpoints."""

    def test_list_workflows(self, client):
        response = client.get("/api/v1/workflows/")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert len(data["workflows"]) >= 2

    def test_run_sequential_workflow(self, client):
        response = client.post(
            "/api/v1/workflows/run",
            json={
                "workflow_type": "sequential",
                "task": "Research and plan AI agents",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] in ("success", "partial", "failed")

    def test_run_unknown_workflow_returns_404(self, client):
        response = client.post(
            "/api/v1/workflows/run",
            json={"workflow_type": "nonexistent", "task": "test"},
        )
        assert response.status_code == 404


class TestMetricsRoutes:
    """Tests for metrics API endpoints."""

    def test_get_metrics(self, client):
        response = client.get("/api/v1/metrics/")
        assert response.status_code == 200
        data = response.json()
        assert "counters" in data
        assert "uptime_seconds" in data

    def test_prometheus_metrics(self, client):
        response = client.get("/api/v1/metrics/prometheus")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
