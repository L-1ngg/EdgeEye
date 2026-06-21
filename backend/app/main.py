from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.services.camera_bridge import camera_bridge_service


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    camera_bridge_service.start()
    try:
        yield
    finally:
        camera_bridge_service.stop()


def create_app() -> FastAPI:
    uploads_dir = Path(settings.uploads_dir)
    reports_dir = Path(settings.reports_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="EdgeEye backend API skeleton",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
    app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")
    register_exception_handlers(app)
    return app


app = create_app()
