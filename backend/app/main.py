from fastapi import FastAPI
from app.api.router import api_router
from app.core.database import Base, engine
import os

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(api_router)


if os.getenv("ENV") == "prod":
    print("🚀 Running in PRODUCTION")
else:
    print("🛠 Running in DEV")