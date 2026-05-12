from app.api.routes.order import router
from app.service_factory import create_service_app

app = create_service_app("order-service", router)
