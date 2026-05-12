from enum import Enum


class OrderStatus(str, Enum):
    INIT = "INIT"
    PAID = "PAID"
    UNLOCKING = "UNLOCKING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class DeviceStatus(str, Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"
