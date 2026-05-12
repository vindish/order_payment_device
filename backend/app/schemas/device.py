from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class DeviceCreate(BaseModel):
    sn: str
    name: str | None = None


class DeviceOut(BaseModel):
    id: int
    sn: str
    name: str | None
    status: str
    last_seen_at: datetime | None

    class Config:
        from_attributes = True


class DeviceCredentialOut(DeviceOut):
    device_secret: str


class DeviceShadowIn(BaseModel):
    desired_state: dict[str, Any] | None = None
    reported_state: dict[str, Any] | None = None


class DeviceShadowOut(BaseModel):
    device_id: int
    desired_state: dict[str, Any]
    reported_state: dict[str, Any]
    version: int


class DeviceCommandIn(BaseModel):
    command: str
    payload: dict[str, Any] = {}
    idempotency_key: str | None = None


class DeviceCommandAckIn(BaseModel):
    command_id: int
    status: str = "ACKED"
    error_message: str | None = None


class TelemetryIn(BaseModel):
    metric: str
    value: Decimal
    unit: str | None = None
    recorded_at: datetime | None = None
