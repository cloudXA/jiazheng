import pytest

from app.config import Settings


def test_production_rejects_placeholder_secrets() -> None:
    settings = Settings(
        app_env="production",
        app_secret_key="example-change-before-production",
        database_url="mysql+asyncmy://example:example@mysql/domestic_risk",
        wechat_app_id="example",
        wechat_app_secret="example",
    )

    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        settings.validate_runtime()
