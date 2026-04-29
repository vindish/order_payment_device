ORDER_FLOW = {
    "INIT": ["PAID"],
    "PAID": ["DONE"],
    "DONE": []
}

def can_transfer(old, new):
    return new in ORDER_FLOW.get(old, [])