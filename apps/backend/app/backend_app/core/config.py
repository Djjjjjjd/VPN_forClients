from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    public_base_url: str = "https://vpn.example.com"
    internal_api_token: str = "change-me"
    artifacts_dir: Path = Field(default=Path("artifacts"))

    database_url: str = "postgresql+asyncpg://vpn:vpn@127.0.0.1:5432/vpn"

    telegram_bot_token: str = "change-me"
    telegram_webhook_secret: str = "change-me"

    yookassa_shop_id: str = "change-me"
    yookassa_secret_key: str = "change-me"
    yookassa_webhook_secret: str = "change-me"
    yookassa_return_url: str = "https://vpn.example.com/payments/return"

    vpn_ssh_username: str = "vpnrunner"
    vpn_ssh_private_key_path: str = "/opt/vpn/.ssh/id_ed25519"
    vpn_ssh_port: int = 22
    vpn_remote_scripts_dir: str = "/usr/local/bin"

    default_country_code: str = "nl"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings
