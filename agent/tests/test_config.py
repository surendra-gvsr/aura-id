# agent/tests/test_config.py
import os
import importlib
import pytest
from unittest.mock import patch


class TestAgentConfig:
    def test_default_poll_interval(self):
        with patch.dict(os.environ, {}, clear=True):
            import src.config as mod

            importlib.reload(mod)
            config = mod.AgentConfig(_env_file=None)
            assert config.poll_interval_seconds == 3

    def test_default_timeouts(self):
        with patch.dict(os.environ, {}, clear=True):
            import src.config as mod

            importlib.reload(mod)
            config = mod.AgentConfig(_env_file=None)
            assert config.api_timeout_connect == 5
            assert config.api_timeout_read == 10

    def test_env_var_overrides_default(self):
        with patch.dict(os.environ, {"AURA_POLL_INTERVAL_SECONDS": "5"}, clear=True):
            import src.config as mod

            importlib.reload(mod)
            config = mod.AgentConfig(_env_file=None)
            assert config.poll_interval_seconds == 5
