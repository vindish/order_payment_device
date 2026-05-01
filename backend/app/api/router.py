from fastapi import APIRouter
from app.api.routes import auth, user, device, order,payment


api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(device.router)


api_router.include_router(order.router)
api_router.include_router(payment.router)