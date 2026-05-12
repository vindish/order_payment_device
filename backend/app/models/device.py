from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base
from app.domain.enums import DeviceStatus


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    sn = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=True)
    secret_hash = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default=DeviceStatus.OFFLINE.value)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
