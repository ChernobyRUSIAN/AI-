from fastapi import FastAPI

from vuls.api.routes import health, internal, telegram
from vuls.core.config import Settings, load_settings
from vuls.runtime.container import RuntimeContainer, build_runtime_container


def create_api_app(
    *,
    settings: Settings | None = None,
    runtime: RuntimeContainer | None = None,
    build_runtime: bool = True,
    telegram_webhook_secret: str | None = None,
) -> FastAPI:
    app_settings = settings or (runtime.settings if runtime is not None else load_settings())
    app_runtime = runtime
    if app_runtime is None and build_runtime:
        app_runtime = build_runtime_container(settings=app_settings)

    app = FastAPI(title="Vuls API", version="v1.0")
    app.state.settings = app_settings
    app.state.runtime = app_runtime
    app.state.telegram_webhook_secret = (
        telegram_webhook_secret or app_settings.telegram_webhook_secret
    )

    app.include_router(health.router)
    app.include_router(telegram.router)
    app.include_router(internal.router)

    return app
