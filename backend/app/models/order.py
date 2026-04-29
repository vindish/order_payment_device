from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(Integer, ForeignKey("devices.id"))

    status = Column(String, default="INIT")  # INIT / PAID / DONE