# Code Map

## Repository Root

```text
README.md          # human-facing overview and quick start
docs/              # deeper documentation and AI context
docker/            # Compose, Dockerfiles, Mosquitto config
backend/           # FastAPI backend and migrations
frontend/          # Next.js frontend
device/            # device-side examples
run.bat            # Windows helper
dev.bat            # Windows helper
prod.bat           # Windows helper
backend.env        # backend env sample/local env file
```

## Backend

### Application Entrypoints

- `backend/app/main.py`: aggregate FastAPI app, health endpoint, CORS, OpenAPI Bearer scheme.
- `backend/app/main_user.py`: user-service entrypoint.
- `backend/app/main_order.py`: order-service entrypoint.
- `backend/app/main_payment.py`: payment-service entrypoint.
- `backend/app/main_device.py`: device-service entrypoint.
- `backend/app/service_factory.py`: shared factory used by split service apps.

### Routes

- `backend/app/api/router.py`: mounts all aggregate API routers.
- `backend/app/api/routes/auth.py`: login, refresh, logout.
- `backend/app/api/routes/user.py`: current user.
- `backend/app/api/routes/device.py`: device CRUD, heartbeat, shadow, commands, ACK, telemetry.
- `backend/app/api/routes/order.py`: create/list orders.
- `backend/app/api/routes/payment.py`: payment callback.

### Services

- `backend/app/services/auth_service.py`: user login, refresh token issue/refresh/logout.
- `backend/app/services/user_service.py`: user-related business logic.
- `backend/app/services/order_service.py`: order creation, listing, status updates.
- `backend/app/services/payment_service.py`: callback verification, order payment transition, outbox publish.
- `backend/app/services/device_service.py`: device creation, credentials, command issue/ACK, shadow, telemetry.
- `backend/app/services/outbox_service.py`: enqueue and dispatch outbox events.

### Infrastructure

- `backend/app/core/config.py`: environment-backed settings.
- `backend/app/core/database.py`: SQLAlchemy engine/session/base.
- `backend/app/core/security.py`: password hashing, JWT, secrets, signatures.
- `backend/app/core/rbac.py`: role enum and dependencies.
- `backend/app/core/idempotency.py`: idempotency key logic.
- `backend/app/core/payment_signing.py`: payment callback canonical payload and signature verification.
- `backend/app/core/event_bus.py`: event publishing facade backed by outbox.
- `backend/app/core/celery_app.py`: Celery app, queues, routes, beat schedule.
- `backend/app/core/mqtt.py`: MQTT client and publish wrapper.

### Domain

- `backend/app/domain/enums.py`: order and device status enums.
- `backend/app/domain/order_flow.py`: allowed order status transitions.

### Models

- `backend/app/models/user.py`: users.
- `backend/app/models/security.py`: refresh tokens and idempotency keys.
- `backend/app/models/device.py`: devices.
- `backend/app/models/order.py`: orders.
- `backend/app/models/iot.py`: shadow, commands, telemetry, rules.
- `backend/app/models/messaging.py`: outbox and dead letters.
- `backend/app/models/__init__.py`: model registration helpers.

### Repositories

- `backend/app/repository/user_repo.py`: user queries.
- `backend/app/repository/device_repo.py`: device queries.
- `backend/app/repository/order_repo.py`: order queries, including row locks.

### Tasks

- `backend/app/tasks/device_tasks.py`: outbox dispatcher task and order-paid unlock task.

### Scripts

- `backend/app/scripts/init_admin.py`: seeds or promotes the admin user.
- `backend/app/scripts/prepare_migrations.py`: compatibility preparation before Alembic upgrade.

### Migrations

- `backend/alembic/env.py`: Alembic environment.
- `backend/alembic/versions/202605120001_initial_schema.py`: initial schema.
- `backend/alembic/versions/202605120002_platform_security_iot.py`: security, messaging, IoT additions.

## Frontend

- `frontend/app/page.tsx`: single-page H5 console for login, device creation, order creation, payment simulation, list views.
- `frontend/app/layout.tsx`: app layout metadata/shell.
- `frontend/app/styles.css`: global styles.
- `frontend/lib/api.ts`: typed API wrapper functions.
- `frontend/lib/request.ts`: fetch wrapper and API base URL config.
- `frontend/package.json`: Next.js scripts and dependencies.

## Docker

- `docker/docker-compose.yml`: full local stack.
- `docker/Dockerfile`: backend image.
- `docker/frontend.Dockerfile`: frontend image.
- `docker/backend-entrypoint.sh`: runs migration/admin seed before starting backend command.
- `docker/mosquitto.conf`: MQTT broker config.

## Device

- `device/esp32/main.ino`: current ESP32 placeholder. Implement Wi-Fi, MQTT subscribe, command handling, and HTTP ACK here when building real device firmware.
