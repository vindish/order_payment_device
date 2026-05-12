from datetime import datetime

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
