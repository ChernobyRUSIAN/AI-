from fastapi import FastAPI

from vuls.api.app import create_api_app
from vuls.core.config import Settings, load_settings
from vuls.core.logging import configure_logging
from vuls.runtime.container import RuntimeContainer


def create_app(
    settings: Settings | None = None,
    runtime: RuntimeContainer | None = None,
) -> FastAPI:
    app_settings = settings or load_settings()
    configure_logging(app_settings.log_level)

    app = create_api_app(
        settings=app_settings,
        runtime=runtime,
        build_runtime=runtime is None,
    )
    app.debug = app_settings.app_env == "local"
    return app


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
