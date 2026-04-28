from pydantic import BaseModel

class DeviceCreate(BaseModel):
    sn: str

class DeviceOut(BaseModel):
    id: int
    sn: str
    status: str

    class Config:
        from_attributes = True