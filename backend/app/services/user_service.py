from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password

def create_user(db: Session, username, password):
    user = User(username=username, password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
