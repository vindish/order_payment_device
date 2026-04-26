from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import create_token

router = APIRouter()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    return {"access_token": create_token({"sub": username})}
