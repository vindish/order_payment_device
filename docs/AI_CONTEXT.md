# AI Context

This file is the fastest entry point for AI agents and new maintainers. Prefer reading it before opening implementation files.

## Project In One Paragraph

Order Payment Device is an event-driven order-payment-unlock platform. A user logs in, creates a device and an order, receives a payment callback, writes an `ORDER_PAID` outbox event, dispatches it through Celery/RabbitMQ, publishes an MQTT unlock command to `device/{sn}/cmd`, then accepts device ACK/telemetry/unlocked events to finish the order.

## Runtime Shape

- Main API: `backend/app/main.py`, exposed on `8000`.
- Split service entrypoints:
  - `backend/app/main_user.py` on `8101`
  - `backend/app/main_order.py` on `8102`
  - `backend/app/main_payment.py` on `8103`
  - `backend/app/main_device.py` on `8104`
- Frontend: `frontend/app/page.tsx`, exposed on `3000`.
- Compose file: `docker/docker-compose.yml`.
- Database: PostgreSQL, migrations in `backend/alembic`.
- Async: Celery broker is RabbitMQ, result backend is Redis.
- Device messaging: Mosquitto MQTT.

The split services are separate FastAPI entrypoints in one monorepo with shared DB/models. Treat them as a deployable service-boundary prototype, not fully independent microservices.

## Critical Flow

1. `POST /api/v1/auth/login` returns access and refresh tokens.
2. `POST /api/v1/devices` creates a device and returns `device_secret` once.
3. `POST /api/v1/orders` creates an `INIT` order for a device.
4. `POST /api/v1/payments/callback`, `/callback/wechat`, or `/callback/alipay` accepts a paid callback.
5. `PaymentService` locks the order, sets it to `PAID`, and writes `ORDER_PAID` to `outbox_events`.
6. `dispatch_outbox_task` publishes due outbox rows to Celery.
7. `handle_order_paid_task` changes order to `UNLOCKING` and calls `DeviceService.issue_command`.
8. `DeviceService.issue_command` writes `device_commands`, publishes MQTT, and marks the command `SENT`.
9. Device calls `/devices/commands/ack` and later `/devices/events/unlocked?order_id=...`.
10. `OrderService.update_status` moves `UNLOCKING -> DONE`.

## Key Files

- `backend/app/services/payment_service.py`: payment callbacks, signature/token fallback, outbox enqueue.
- `backend/app/services/order_service.py`: order creation and status transitions.
- `backend/app/services/device_service.py`: device credentials, heartbeat, shadow, telemetry, command issue/ACK.
- `backend/app/services/outbox_service.py`: reliable event dispatch and dead-letter handling.
- `backend/app/tasks/device_tasks.py`: Celery tasks for outbox and unlock command flow.
- `backend/app/domain/order_flow.py`: allowed order status transitions.
- `backend/app/core/idempotency.py`: idempotency key reservation/replay.
- `backend/app/core/rbac.py`: role hierarchy.
- `backend/app/core/mqtt.py`: MQTT publish wrapper with degraded logging fallback.

## Auth Model

- User API auth uses Bearer JWT.
- Role levels: `admin` 100, `operator` 50, `user` 10, `device` 10.
- Device API auth uses headers:
  - `X-Device-SN`
  - `X-Device-Token`
- Device token is a generated secret returned during device creation. Only its hash is stored.
- Manual payment callback uses HMAC signature if provided and falls back to `PAYMENT_CALLBACK_TOKEN`.
- WeChat Pay APIv3 and Alipay callbacks use provider signatures and `out_trade_no`.

## Important State Values

Order status:

- `INIT`
- `PAID`
- `UNLOCKING`
- `DONE`
- `FAILED`
- `CANCELED`

Device status:

- `offline`
- `online`
- `busy`
- `error`

Device command status is string-based. Current flow creates `PENDING`, sends MQTT, marks `SENT`, then accepts device-provided ACK status such as `ACKED`.

## Data Tables To Know

- `users`
- `refresh_tokens`
- `devices`
- `orders`
- `idempotency_keys`
- `outbox_events`
- `dead_letter_events`
- `device_commands`
- `device_shadows`
- `telemetry_points`
- `rule_definitions`

## Default Local Credentials

- Admin: `admin / 123456`
- RabbitMQ: `app / app123`
- PostgreSQL: `app / app123`, database `app_db`

Production must override secrets.

## Typical Verification

```bash
docker compose -f docker/docker-compose.yml up -d --build
curl http://localhost:8000/health
docker compose -f docker/docker-compose.yml ps
```

Expected health body:

```json
{"status":"ok","service":"Order Payment Device","env":"prod"}
```

## Known Gaps

- Live payment provider credentials and certificates still need to be supplied for production use.
- ESP32 code is only a minimal skeleton.
- Telemetry uses PostgreSQL, not a dedicated time-series store.
- Services share one database and one codebase.
- Celery worker should run as a non-root user in production.
