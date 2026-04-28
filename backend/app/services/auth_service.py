from app.repository.user_repo import UserRepository
from app.core.security import verify_password, create_access_token

class AuthService:
    def __init__(self, db):
        self.repo = UserRepository(db)

    def login(self, username: str, password: str):
        user = self.repo.get_by_username(username)

        if not user:
            raise Exception("用户不存在")

        if not verify_password(password, user.password):
            raise Exception("密码错误")

        token = create_access_token({"sub": str(user.id)})

        return token