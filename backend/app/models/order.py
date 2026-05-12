from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from app.core.database import Base
from app.domain.enums import OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="CNY")
    status = Column(String(32), nullable=False, default=OrderStatus.INIT.value, index=True)
    payment_provider = Column(String(32), nullable=True)
    payment_trade_no = Column(String(128), nullable=True, index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(String(512), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    unlocked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
