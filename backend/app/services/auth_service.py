from datetime import datetime

from fastapi import HTTPException

from app.core.security import create_access_token, create_refresh_token, hash_token, verify_password
from app.models.security import RefreshToken
from app.repository.user_repo import UserRepository


class AuthService:
    def __init__(self, db):
        self.db = db
        self.repo = UserRepository(db)

    def login(self, username: str, password: str):
        user = self.repo.get_by_username(username)

        if not user or not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is disabled")

        return self._issue_tokens(user)

    def refresh(self, refresh_token: str):
        token_hash = hash_token(refresh_token)
        record = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
            .first()
        )
        if not record or record.expires_at <= datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

        user = self.repo.get_by_id(record.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User invalid or disabled")

        record.revoked_at = datetime.utcnow()
        return self._issue_tokens(user)

    def logout(self, refresh_token: str):
        record = self.db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(refresh_token)).first()
        if record and record.revoked_at is None:
            record.revoked_at = datetime.utcnow()
            self.db.commit()
        return {"msg": "Logged out"}

    def _issue_tokens(self, user):
        refresh_token, token_hash, expires_at = create_refresh_token()
        self.db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        self.db.commit()
        return {
            "access_token": create_access_token({"sub": str(user.id), "role": user.role}),
            "refresh_token": refresh_token,
        }
