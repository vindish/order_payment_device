from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username
    }