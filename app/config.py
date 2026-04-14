from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = "test"
    telegram_api_server: str = ""  # e.g. https://my-worker.workers.dev (proxy when api.telegram.org is blocked)
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./marketplace.db"
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    public_web_url: str = ""  # e.g. https://xxx.trycloudflare.com; empty => localhost URL
    web_secret: str = "change-me"
    web_admin_password: str = "change-me"  # password for SQLAdmin /admin login
    daily_placement_fee: int = 50
    demo_mode: bool = True  # show admin UI to everyone, block mutating actions
    yandex_metrika_id: str = ""
    google_analytics_id: str = ""
    ga_api_secret: str = ""

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x) for x in self.admin_ids.split(",") if x.strip()]


settings = Settings()
