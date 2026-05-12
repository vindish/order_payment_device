from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def create_service_app(name: str, router: APIRouter) -> FastAPI:
    app = FastAPI(title=name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health_check():
        return {"status": "ok", "service": name, "env": settings.ENV}

    app.include_router(router, prefix=settings.API_PREFIX)
    return app
