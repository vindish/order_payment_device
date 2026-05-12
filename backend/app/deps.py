from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_access_token, verify_password
from app.repository.device_repo import DeviceRepository
from app.repository.user_repo import UserRepository


# ===== 数据库 =====
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== JWT =====
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="BearerAuth"
)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效")

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效")

    repo = UserRepository(db)
    user = repo.get_by_id(int(user_id))

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return user


def get_current_device(
    x_device_sn: str = Header(alias="X-Device-SN"),
    x_device_token: str = Header(alias="X-Device-Token"),
    db: Session = Depends(get_db),
):
    device = DeviceRepository(db).get_by_sn(x_device_sn)
    if not device or not device.secret_hash:
        raise HTTPException(status_code=401, detail="Device credentials invalid")
    if not verify_password(x_device_token, device.secret_hash):
        raise HTTPException(status_code=401, detail="Device credentials invalid")
    return device
