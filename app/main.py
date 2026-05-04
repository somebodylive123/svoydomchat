from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.debug import router as debug_router
from app.api.routes.health import router as health_router
from app.api.routes.whatsapp import router as whatsapp_router
from app.config import settings
from app.database.session import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(whatsapp_router)
    app.include_router(debug_router)

    return app


app = create_app()
