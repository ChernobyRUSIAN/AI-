from fastapi import FastAPI

from vuls.api.routes import health, internal, telegram


def create_api_app(telegram_webhook_secret: str = "test-secret") -> FastAPI:
    app = FastAPI(title="Vuls API", version="v1.0")
    app.state.telegram_webhook_secret = telegram_webhook_secret

    app.include_router(health.router)
    app.include_router(telegram.router)
    app.include_router(internal.router)

    return app
