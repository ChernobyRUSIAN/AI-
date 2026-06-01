from fastapi import FastAPI

from vuls.core.config import Settings, load_settings
from vuls.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings()
    configure_logging(app_settings.log_level)

    return FastAPI(
        title="Vuls",
        version="0.1.0",
        debug=app_settings.app_env == "local",
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "vuls.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()
