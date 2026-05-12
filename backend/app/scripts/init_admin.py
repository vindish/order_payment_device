import os

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main():
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "123456")

    db = SessionLocal()
    try:
        if not db.query(User).filter_by(username=username).first():
            db.add(User(username=username, password=hash_password(password)))
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
