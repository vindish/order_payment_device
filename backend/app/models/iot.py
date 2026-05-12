from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.core.database import Base


class DeviceShadow(Base):
    __tablename__ = "device_shadows"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, unique=True, index=True)
    desired_state = Column(Text, nullable=False, default="{}")
    reported_state = Column(Text, nullable=False, default="{}")
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeviceCommand(Base):
    __tablename__ = "device_commands"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    command = Column(String(64), nullable=False, index=True)
    payload = Column(Text, nullable=False, default="{}")
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    acked_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class TelemetryPoint(Base):
    __tablename__ = "telemetry_points"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    metric = Column(String(64), nullable=False, index=True)
    value = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(32), nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class RuleDefinition(Base):
    __tablename__ = "rule_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    metric = Column(String(64), nullable=False, index=True)
    operator = Column(String(16), nullable=False)
    threshold = Column(Numeric(18, 6), nullable=False)
    action = Column(String(64), nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
