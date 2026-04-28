from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()

if not db.query(User).filter_by(username="admin").first():
    user = User(
        username="admin",
        password=hash_password("123456")
    )
    db.add(user)
    db.commit()

db.close()