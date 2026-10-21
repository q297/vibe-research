import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router_v1
from app.config import get_settings
from app.context import TRACE_HEADER, TraceMiddleware
from app.errors import install_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    app = FastAPI(
        title="Alfa News Insights API",
        version=settings.app_version,
        description="BFF for the news analytics prototype. Mock mode serves synthetic fixtures",
    )
    app.add_middleware(TraceMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[TRACE_HEADER],
    )
    install_error_handlers(app)
    app.include_router(router_v1)
    return app


app = create_app()
