from fastapi import FastAPI
from app.api.router import api_router
from app.core.database import Base, engine
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Device System",
        version="1.0",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema




app = FastAPI(title="Device System")
app.openapi = custom_openapi

# 创建表（开发阶段用）
Base.metadata.create_all(bind=engine)

app.include_router(api_router)