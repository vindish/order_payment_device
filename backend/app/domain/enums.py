from enum import Enum

class OrderStatus(str, Enum):
    INIT = "INIT"
    PAID = "PAID"
    DONE = "DONE"