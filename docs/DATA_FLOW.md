# Data Flow

## Order Status Machine

Allowed transitions are defined in `backend/app/domain/order_flow.py`.

```text
INIT       -> PAID, CANCELED
PAID       -> UNLOCKING, FAILED
UNLOCKING  -> DONE, FAILED
FAILED     -> UNLOCKING, CANCELED
DONE       -> terminal
CANCELED   -> terminal
```

Any invalid transition raises `400 Invalid state transition`.

## Payment-To-Unlock Flow

```text
Client
  |
  | POST /orders
  v
OrderService.create_order
  |
  | creates orders.status = INIT
  v
Payment provider / manual callback
  |
  | POST /payments/callback
  v
PaymentService.handle_callback
  |
  | validates signature/token
  | reserves/replays idempotency key
  | locks order row
  | INIT -> PAID
  | writes outbox_events ORDER_PAID
  v
dispatch_outbox_task
  |
  | reads PENDING outbox rows
  | sends Celery task
  | marks outbox PUBLISHED
  v
handle_order_paid_task
  |
  | PAID -> UNLOCKING
  | creates device_commands
  | publishes MQTT
  v
device/{sn}/cmd
  |
  v
Device
  |
  | POST /devices/commands/ack
  | POST /devices/events/unlocked?order_id=...
  v
OrderService.update_status
  |
  | UNLOCKING -> DONE
  v
Order complete
```

## Idempotency

Implemented in `backend/app/core/idempotency.py`.

Used by:

- `OrderService.create_order`
- `PaymentService.handle_callback`

Mechanism:

1. Hash request payload.
2. If key is new, reserve it in `idempotency_keys`.
3. If key exists with same scope and payload hash, replay stored response.
4. If key exists with different scope or payload hash, return `409`.
5. Store response after successful operation.

For payment callbacks, the effective key is `Idempotency-Key` header or `trade_no`.

## Outbox States

Table: `outbox_events`.

Common statuses:

- `PENDING`: committed but not dispatched.
- `PUBLISHED`: task was queued.
- `DEAD`: retries exhausted during dispatch.

Dispatch selection:

- `status = PENDING`
- `next_attempt_at <= now`
- row is not locked, or lock is older than five minutes

The dispatcher uses `with_for_update(skip_locked=True)` for concurrent safety.

## Dead Letter Handling

Table: `dead_letter_events`.

Written when:

- outbox dispatch fails repeatedly.
- device command task reaches max retries.

Check dead letters when orders are stuck in `PAID`, `UNLOCKING`, or `FAILED`.

## Device Command Flow

Command creation:

1. `DeviceService.issue_command` receives command and payload.
2. It checks `device_commands.idempotency_key`.
3. It inserts a command row with `PENDING`.
4. It publishes MQTT payload to `device/{sn}/cmd`.
5. It marks command `SENT`.

ACK:

1. Device calls `POST /devices/commands/ack`.
2. Server verifies `X-Device-SN` and `X-Device-Token`.
3. Server locks command row by command ID and device ID.
4. Server sets the device-provided status and `acked_at`.

## Device Telemetry

Endpoint: `POST /devices/telemetry`.

Effect:

- Inserts a row into `telemetry_points`.
- Updates `devices.last_seen_at`.
- Marks device `online`.

This is sufficient for low-volume telemetry. For high-frequency production data, replace or augment it with a time-series store.

## Device Shadow

Endpoints:

- `GET /devices/{sn}/shadow`
- `PUT /devices/{sn}/shadow`

Shadow table:

- `desired_state`: target state controlled by backend/operator.
- `reported_state`: latest state reported by device or operator update.
- `version`: increments on update.
