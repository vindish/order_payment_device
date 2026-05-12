from app.api.routes.device import router
from app.service_factory import create_service_app

app = create_service_app("device-service", router)
