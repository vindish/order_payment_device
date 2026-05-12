from app.models.order import Order

class OrderRepository:
    def __init__(self, db):
        self.db = db

    def create(self, order: Order):
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_by_id(self, order_id: int):
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_by_id_for_update(self, order_id: int):
        return self.db.query(Order).filter(Order.id == order_id).with_for_update().first()

    def list_by_user(self, user_id: int):
        return self.db.query(Order).filter(Order.user_id == user_id).all()

    def update(self, order: Order):
        self.db.commit()
        self.db.refresh(order)
        return order
