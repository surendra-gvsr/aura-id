# agent/src/config.py
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AURA_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    api_base_url: AnyHttpUrl = AnyHttpUrl("https://api.auraid.com/v1")
    workstation_token: str = ""
    poll_interval_seconds: int = 3
    api_timeout_connect: int = 5
    api_timeout_read: int = 10
    sentry_dsn: str = ""
    update_check_url: str = "https://updates.auraid.com/latest.json"
    app_version: str = "0.1.0"
