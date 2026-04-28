from fastapi import FastAPI
from app.api.router import api_router
from app.core.database import Base, engine

app = FastAPI(title="Device System")

# 创建表（开发阶段用）
Base.metadata.create_all(bind=engine)

app.include_router(api_router)