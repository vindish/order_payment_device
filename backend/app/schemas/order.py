from pydantic import BaseModel

class OrderCreate(BaseModel):
    device_sn: str


class OrderOut(BaseModel):
    id: int
    user_id: int
    device_id: int
    status: str

    class Config:
        from_attributes = True