"""FastAPI application factory and runtime entrypoint.

The database engine is created lazily inside the lifespan, so importing this
module (e.g. ``uvicorn app.main:app``) never touches the filesystem.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.api.errors import register_exception_handlers
from app.api.routes import router as api_router
from app.api.spa import mount_frontend_spa
from app.core import lifecycle
from app.core.config import get_settings
from app.modules.storage.database import create_db_engine, init_db, session_factory_for


def create_app(engine: Engine | None = None) -> FastAPI:
    """Builds the FastAPI application.

    ``engine`` overrides the settings-resolved database URL (used by tests to
    inject an in-memory engine).
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        resolved_engine = engine if engine is not None else create_db_engine(get_settings().database_url)
        app.state.engine = resolved_engine
        app.state.session_factory = session_factory_for(resolved_engine)
        init_db(resolved_engine)
        try:
            yield
        finally:
            resolved_engine.dispose()

    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def track_client_activity(request: Request, call_next):
        # Any request proves a client is still around; the packaged launcher's
        # idle watchdog reads this clock to auto-exit once the tabs are closed.
        lifecycle.touch()
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(api_router)
    mount_frontend_spa(app)

    return app


app = create_app()
