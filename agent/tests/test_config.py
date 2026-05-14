# agent/tests/test_config.py
import importlib
import os
from unittest.mock import patch

import pytest


def _aura_env(**overrides):
    """Return an env dict with all AURA_* keys stripped, plus any overrides."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith("AURA_")}
    clean.update(overrides)
    return clean


class TestAgentConfig:
    def test_default_poll_interval(self):
        with patch.dict(os.environ, _aura_env(), clear=False):
            import src.config as mod

            importlib.reload(mod)
            config = mod.AgentConfig(_env_file=None)
            assert config.poll_interval_seconds == 3

    def test_default_timeouts(self):
        with patch.dict(os.environ, _aura_env(), clear=False):
            import src.config as mod

            importlib.reload(mod)
            config = mod.AgentConfig(_env_file=None)
            assert config.api_timeout_connect == 5
            assert config.api_timeout_read == 10

    def test_env_var_overrides_default(self):
        with patch.dict(
            os.environ, _aura_env(AURA_POLL_INTERVAL_SECONDS="5"), clear=False
        ):
            import src.config as mod

            importlib.reload(mod)
            config = mod.AgentConfig(_env_file=None)
            assert config.poll_interval_seconds == 5
