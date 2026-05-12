from fastapi import APIRouter

from app.api.routes import auth, user
from app.service_factory import create_service_app

router = APIRouter()
router.include_router(auth.router)
router.include_router(user.router)

app = create_service_app("user-service", router)
