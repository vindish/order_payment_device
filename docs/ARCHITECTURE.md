# Architecture

## High-Level Components

```text
Browser / H5 Console
        |
        v
FastAPI aggregate API :8000
        |
        +--> PostgreSQL
        +--> RabbitMQ <--> Celery worker / beat
        +--> Redis result backend
        +--> MQTT broker --> Device topic device/{sn}/cmd
```

The same codebase also exposes four domain-oriented service entrypoints:

```text
user-service    :8101 -> auth + users
order-service   :8102 -> orders
payment-service :8103 -> payment callbacks
device-service  :8104 -> devices, shadow, telemetry, commands
```

These entrypoints are useful for validating service boundaries and deployment topology. They currently share SQLAlchemy models, migrations, database, broker, and codebase.

## Backend Layers

```text
api/routes  -> request/response boundary
schemas     -> Pydantic DTOs
services    -> business workflows and transaction decisions
repository  -> SQLAlchemy data access
models      -> database tables
domain      -> state machines and domain enums
core        -> infrastructure: config, auth, DB, Celery, MQTT, idempotency
tasks       -> asynchronous workers
```

Service methods are the main place to add business behavior. Routes should stay thin.

## Data Consistency Pattern

Payment callback handling uses a transactional outbox:

1. Lock the order row.
2. Validate transition to `PAID`.
3. Update payment fields.
4. Insert an `outbox_events` row.
5. Commit.
6. Trigger `dispatch_outbox_task`.

If dispatch fails, the committed outbox row remains available for Celery beat to retry every five seconds.

Supported payment callback entrypoints:

- `POST /api/v1/payments/callback`
- `POST /api/v1/payments/callback/wechat`
- `POST /api/v1/payments/callback/alipay`

## Async Processing

Celery configuration is in `backend/app/core/celery_app.py`.

Queues:

- `default`
- `outbox`
- `device_commands`

Task routes:

- `app.tasks.device_tasks.dispatch_outbox_task` -> `outbox`
- `app.tasks.device_tasks.handle_order_paid_task` -> `device_commands`

Beat schedule:

- `dispatch-outbox-every-5s`: runs outbox dispatch every five seconds.

Retry behavior:

- Device command task uses Celery autoretry with exponential backoff, jitter, and max 5 retries.
- On final failure it marks the order `FAILED` and writes `dead_letter_events`.

## MQTT Contract

Command topic:

```text
device/{sn}/cmd
```

Payload shape:

```json
{
  "command_id": 1,
  "cmd": "unlock",
  "payload": {
    "order_id": 1
  }
}
```

The device should ACK by calling the HTTP endpoint `POST /api/v1/devices/commands/ack`.

## Authentication Boundaries

User/operator/admin requests:

- Use `Authorization: Bearer <access_token>`.
- Created by `POST /api/v1/auth/login`.
- Role checks are implemented in `backend/app/core/rbac.py`.

Device requests:

- Use `X-Device-SN` and `X-Device-Token`.
- Token is generated during `POST /api/v1/devices`.
- Server stores only the token hash.

Payment callback:

- Does not use user JWT.
- Manual callback uses HMAC signature if provided and valid.
- Manual callback falls back to `PAYMENT_CALLBACK_TOKEN` compatibility token.
- WeChat Pay and Alipay callbacks use provider signatures and `out_trade_no`.

## Deployment Notes

`docker/docker-compose.yml` starts:

- `postgres`
- `redis`
- `rabbitmq`
- `mqtt`
- `backend`
- `worker`
- `scheduler`
- `user-service`
- `order-service`
- `payment-service`
- `device-service`
- `frontend`

Only the `backend` container runs migrations and seeds the admin user by default:

- `RUN_MIGRATIONS=1`
- `SEED_ADMIN=1`

Split services use `RUN_MIGRATIONS=0` and depend on the main backend health check.
