from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    sn = Column(String, unique=True, index=True)   # 设备编号
    status = Column(String, default="offline")