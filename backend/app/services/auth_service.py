from fastapi import HTTPException

from app.core.security import create_access_token, verify_password
from app.repository.user_repo import UserRepository


class AuthService:
    def __init__(self, db):
        self.repo = UserRepository(db)

    def login(self, username: str, password: str):
        user = self.repo.get_by_username(username)

        if not user or not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is disabled")

        return create_access_token({"sub": str(user.id)})
