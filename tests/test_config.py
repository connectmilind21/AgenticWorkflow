"""
Tests for the configuration module.
"""

from __future__ import annotations

import yaml

from agentic_workflow.config import (
    APISettings,
    DatabaseSettings,
    LLMSettings,
    ObservabilitySettings,
    Settings,
    get_settings,
)


class TestLLMSettings:
    """Tests for LLMSettings."""

    def test_defaults(self):
        s = LLMSettings()
        assert s.provider == "openai"
        assert s.temperature == 0.1
        assert s.max_tokens == 4096
        assert s.timeout == 60

    def test_custom_values(self):
        s = LLMSettings(model="gpt-3.5-turbo", temperature=0.5)
        assert s.temperature == 0.5


class TestAPISettings:
    """Tests for APISettings."""

    def test_defaults(self):
        s = APISettings()
        assert s.host == "0.0.0.0"
        assert s.port == 8080
        assert s.workers == 4


class TestSettings:
    """Tests for the main Settings class."""

    def test_defaults(self):
        s = Settings()
        assert s.app_name == "Agentic Workflow Framework"
        assert s.app_version == "0.1.0"
        assert s.agent_max_iterations == 10

    def test_from_yaml(self, tmp_path):
        """Loads settings from YAML file."""
        config = {
            "app": {"name": "Custom App", "version": "2.0.0"},
            "agents": {"max_iterations": 15, "max_execution_time": 600},
            "workflows": {"max_parallel_tasks": 10},
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))

        s = Settings.from_yaml(str(config_file))
        assert s.app_name == "Custom App"
        assert s.agent_max_iterations == 15

    def test_sub_settings_are_populated(self):
        """Sub-settings objects are instantiated."""
        s = Settings()
        assert isinstance(s.llm, LLMSettings)
        assert isinstance(s.database, DatabaseSettings)
        assert isinstance(s.api, APISettings)
        assert isinstance(s.observability, ObservabilitySettings)


class TestGetSettings:
    """Tests for the get_settings factory."""

    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_cached(self):
        """Returns the same instance on repeated calls."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
