from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVER_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "家政签约风控服务"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "example-change-before-production"
    access_token_expire_minutes: int = 10080
    database_url: str = "mysql+asyncmy://example:example@127.0.0.1:3306/domestic_risk"
    auto_create_tables: bool = True

    deepseek_enabled: bool = False
    deepseek_api_key: str = "example"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = 30

    wechat_app_id: str = "example"
    wechat_app_secret: str = "example"
    asr_provider: str = "mock"
    tencent_secret_id: str = "example"
    tencent_secret_key: str = "example"
    tencent_asr_region: str = "ap-shanghai"
    tencent_asr_engine: str = "16k_zh"
    tencent_asr_timeout_seconds: int = 20
    tencent_asr_hotword_list: str = ""
    cors_origins: str = "*"

    @property
    def deepseek_configured(self) -> bool:
        return (
            self.deepseek_enabled
            and bool(self.deepseek_api_key)
            and self.deepseek_api_key != "example"
        )

    @property
    def wechat_configured(self) -> bool:
        return (
            bool(self.wechat_app_id)
            and self.wechat_app_id != "example"
            and bool(self.wechat_app_secret)
            and self.wechat_app_secret != "example"
        )

    @property
    def tencent_asr_configured(self) -> bool:
        return (
            self.asr_provider.lower() == "tencent"
            and bool(self.tencent_secret_id)
            and self.tencent_secret_id != "example"
            and bool(self.tencent_secret_key)
            and self.tencent_secret_key != "example"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_runtime(self) -> None:
        if self.app_env != "production":
            return
        if self.app_secret_key.startswith("example"):
            raise RuntimeError("APP_SECRET_KEY must be changed in production")
        if "example" in self.database_url:
            raise RuntimeError("DATABASE_URL must be configured in production")
        if not self.wechat_configured:
            raise RuntimeError("WeChat credentials must be configured in production")
        if self.asr_provider.lower() == "tencent" and not self.tencent_asr_configured:
            raise RuntimeError("Tencent ASR credentials must be configured in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
