# Runbook

## Start Everything

From the repository root:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Check status:

```bash
docker compose -f docker/docker-compose.yml ps
```

Check API health:

```bash
curl http://localhost:8000/health
```

## Stop

```bash
docker compose -f docker/docker-compose.yml down
```

Stop and remove persisted data volumes:

```bash
docker compose -f docker/docker-compose.yml down -v
```

## Logs

API:

```bash
docker compose -f docker/docker-compose.yml logs -f backend
```

Worker:

```bash
docker compose -f docker/docker-compose.yml logs -f worker
```

Scheduler:

```bash
docker compose -f docker/docker-compose.yml logs -f scheduler
```

Frontend:

```bash
docker compose -f docker/docker-compose.yml logs -f frontend
```

## Database

Open psql:

```bash
docker compose -f docker/docker-compose.yml exec postgres psql -U app -d app_db
```

Check migration version:

```bash
docker compose -f docker/docker-compose.yml exec backend alembic current
```

Apply migrations manually:

```bash
docker compose -f docker/docker-compose.yml exec backend alembic upgrade head
```

## RabbitMQ

Management UI:

```text
http://localhost:15672
```

Credentials:

```text
app / app123
```

Important queues:

- `default`
- `outbox`
- `device_commands`

## Smoke Test

1. Login:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'
```

2. Create device with the returned access token:

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"sn":"LOCK-001","name":"测试门锁"}'
```

3. Create order:

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Authorization: Bearer <access_token>" \
  -H "Idempotency-Key: create-order-001" \
  -H "Content-Type: application/json" \
  -d '{"device_sn":"LOCK-001","amount":"1.00"}'
```

4. Simulate payment callback:

```bash
curl -X POST http://localhost:8000/api/v1/payments/callback \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: payment-001" \
  -d '{"order_id":1,"provider":"manual","trade_no":"manual-001","status":"PAID","token":"replace-with-provider-secret"}'
```

5. Confirm order and command records in PostgreSQL:

```sql
select id, status, retry_count, error_message from orders order by id desc limit 5;
select id, command, status, payload from device_commands order by id desc limit 5;
select id, event_name, status, retry_count, published_at, error_message from outbox_events order by id desc limit 5;
```

## Local Backend Development

Start infrastructure with Compose, then run the API locally:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Use a local `.env` when running outside Compose:

```env
DATABASE_URL=postgresql+psycopg2://app:app123@localhost:5432/app_db
REDIS_HOST=localhost
CELERY_BROKER_URL=amqp://app:app123@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/0
MQTT_HOST=localhost
SECRET_KEY=change-me-but-at-least-16-chars
```

## Local Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Set API base if needed:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

## Common Failures

### API is unhealthy

Check PostgreSQL, RabbitMQ, Redis, and backend logs:

```bash
docker compose -f docker/docker-compose.yml ps postgres rabbitmq redis backend
docker compose -f docker/docker-compose.yml logs --tail=100 backend
```

### Payment callback succeeds but no device command is sent

Check:

- `outbox_events.status`
- worker logs
- RabbitMQ `outbox` and `device_commands` queues
- MQTT container logs

### Device API returns 401

Check that:

- `X-Device-SN` matches a device row.
- `X-Device-Token` is the original `device_secret`.
- The token was not confused with the stored hash.

### Reusing idempotency key returns 409

This is expected when the same idempotency key is reused with a different request payload or scope.
