# Order Payment Device

Order Payment Device 是一个事件驱动的订单支付开锁系统示例。项目包含 FastAPI 后端、Next.js H5 控制台、PostgreSQL、RabbitMQ、Redis、Celery、MQTT、Alembic 数据库迁移、Docker Compose 编排，以及一个 ESP32 设备端示例目录。

系统目标是串起一个典型业务闭环：

1. 管理员或运营人员创建设备。
2. 用户针对设备创建订单。
3. 支付平台回调订单支付成功。
4. 后端通过 outbox pattern 发布 `ORDER_PAID` 事件。
5. Celery worker 消费事件并向 MQTT topic 下发设备开锁命令。
6. 设备上报 ACK、心跳、遥测或开锁完成事件。
7. 订单状态更新为完成。

## 文档入口

- [AI 快速上下文](docs/AI_CONTEXT.md)：给 AI/新维护者的最高密度项目摘要。
- [架构说明](docs/ARCHITECTURE.md)：组件、边界、消息流、服务化形态。
- [运行手册](docs/RUNBOOK.md)：启动、验证、常用命令、排障。
- [API 摘要](docs/API_REFERENCE.md)：当前接口、鉴权方式、示例请求。
- [数据流与状态机](docs/DATA_FLOW.md)：订单状态、支付回调、outbox、设备命令链路。
- [代码地图](docs/CODE_MAP.md)：目录结构和关键文件职责。

## 技术栈

- 后端：Python 3.11、FastAPI、SQLAlchemy、Alembic、Pydantic Settings
- 前端：Next.js 14、React 18、TypeScript、lucide-react
- 数据库：PostgreSQL 15
- 消息与异步：RabbitMQ、Celery、Redis result backend
- 设备通信：Mosquitto MQTT，命令 topic 为 `device/{sn}/cmd`
- 部署：Docker Compose
- 设备示例：`device/esp32/main.ino`

## 服务地址

使用 Docker Compose 启动后，默认端口如下：

| 服务 | 地址 |
| --- | --- |
| 聚合 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 前端控制台 | http://localhost:3000 |
| user-service | http://localhost:8101 |
| order-service | http://localhost:8102 |
| payment-service | http://localhost:8103 |
| device-service | http://localhost:8104 |
| RabbitMQ 管理台 | http://localhost:15672 |
| MQTT | localhost:1883 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

RabbitMQ 默认账号密码为 `app / app123`。

默认管理员为 `admin / 123456`。生产环境必须通过环境变量覆盖 `ADMIN_PASSWORD`、`SECRET_KEY`、`PAYMENT_CALLBACK_TOKEN` 和 `PAYMENT_SIGNING_SECRET`。

## 快速启动

在项目根目录执行：

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

查看容器状态：

```bash
docker compose -f docker/docker-compose.yml ps
```

验证 API：

```bash
curl http://localhost:8000/health
```

预期返回：

```json
{"status":"ok","service":"Order Payment Device","env":"prod"}
```

停止服务：

```bash
docker compose -f docker/docker-compose.yml down
```

如需清空数据库和 MQTT 数据卷：

```bash
docker compose -f docker/docker-compose.yml down -v
```

## 本地开发

后端依赖：

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

本地直接运行后端时，默认配置里的数据库、Redis、MQTT 主机名是 Docker Compose 服务名。若不在 Compose 网络内运行，请设置本地 `.env`，例如：

```env
ENV=dev
SECRET_KEY=change-me-but-at-least-16-chars
DATABASE_URL=postgresql+psycopg2://app:app123@localhost:5432/app_db
REDIS_HOST=localhost
CELERY_BROKER_URL=amqp://app:app123@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/0
MQTT_HOST=localhost
PAYMENT_CALLBACK_TOKEN=replace-with-provider-secret
PAYMENT_SIGNING_SECRET=replace-with-payment-signing-secret
```

运行迁移和 API：

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

运行 worker：

```bash
cd backend
celery -A app.core.celery_app.celery_app worker --loglevel=info -Q default,device_commands,outbox
```

运行 beat：

```bash
cd backend
celery -A app.core.celery_app.celery_app beat --loglevel=info
```

前端开发：

```bash
cd frontend
npm install
npm run dev
```

前端默认读取 `NEXT_PUBLIC_API_BASE_URL`，未设置时使用 `http://localhost:8000/api/v1`。

## 核心业务流程

### 1. 登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'
```

返回 `access_token` 和 `refresh_token`。除支付回调外，大多数管理接口使用 Bearer JWT。

### 2. 创建设备

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"sn":"LOCK-001","name":"测试门锁"}'
```

响应会返回一次性可见的 `device_secret`。设备后续请求需使用请求头：

- `X-Device-SN: LOCK-001`
- `X-Device-Token: <device_secret>`

### 3. 创建订单

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Authorization: Bearer <access_token>" \
  -H "Idempotency-Key: create-order-LOCK-001-001" \
  -H "Content-Type: application/json" \
  -d '{"device_sn":"LOCK-001","amount":"1.00"}'
```

### 4. 模拟支付成功回调

```bash
curl -X POST http://localhost:8000/api/v1/payments/callback \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: payment-order-1" \
  -d '{"order_id":1,"provider":"manual","trade_no":"manual-1","status":"PAID","token":"replace-with-provider-secret"}'
```

支付成功后，系统会写入 outbox 事件，并由 Celery 触发设备开锁命令。

### 5. 设备 ACK 命令

设备收到 MQTT topic `device/{sn}/cmd` 的命令后，可调用：

```bash
curl -X POST http://localhost:8000/api/v1/devices/commands/ack \
  -H "X-Device-SN: LOCK-001" \
  -H "X-Device-Token: <device_secret>" \
  -H "Content-Type: application/json" \
  -d '{"command_id":1,"status":"ACKED"}'
```

设备确认开锁完成后：

```bash
curl -X POST "http://localhost:8000/api/v1/devices/events/unlocked?order_id=1" \
  -H "X-Device-SN: LOCK-001" \
  -H "X-Device-Token: <device_secret>"
```

## 架构概览

Compose 中同时提供一个聚合 API 和四个按领域拆分的 FastAPI 入口：

- `backend/app/main.py`：聚合 API，挂载 auth、user、device、order、payment 路由。
- `backend/app/main_user.py`：用户与认证服务入口。
- `backend/app/main_order.py`：订单服务入口。
- `backend/app/main_payment.py`：支付服务入口。
- `backend/app/main_device.py`：设备服务入口。

当前服务化是单代码库、共享数据库、共享模型的基础形态。它便于验证领域边界和部署拓扑，但还不是物理拆库、拆仓后的最终微服务架构。

## 关键目录

```text
backend/
  app/
    api/routes/       # FastAPI 路由
    core/             # 配置、数据库、鉴权、Celery、MQTT、幂等、签名
    domain/           # 领域枚举与订单状态流转
    models/           # SQLAlchemy 模型
    repository/       # 数据访问层
    schemas/          # Pydantic 请求/响应模型
    services/         # 业务服务
    tasks/            # Celery 任务
    scripts/          # 容器启动辅助脚本
  alembic/            # 数据库迁移
frontend/
  app/                # Next.js 页面和样式
  lib/                # API request 封装
docker/               # Dockerfile、Compose、Mosquitto 配置
device/esp32/         # ESP32 示例代码
docs/                 # 项目说明和 AI 上下文
```

## 配置项

主要环境变量：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `ENV` | 运行环境 | `dev` |
| `SECRET_KEY` | JWT 签名密钥 | `change-me-in-production` |
| `DATABASE_URL` | SQLAlchemy 数据库连接 | Compose 内 PostgreSQL |
| `BACKEND_CORS_ORIGINS` | CORS 白名单，逗号分隔 | `http://localhost:3000,http://127.0.0.1:3000` |
| `REDIS_HOST` | Redis 主机 | `redis` |
| `CELERY_BROKER_URL` | Celery broker | 未设置时退回 Redis |
| `CELERY_RESULT_BACKEND` | Celery result backend | 未设置时退回 Redis |
| `MQTT_HOST` | MQTT broker 主机 | `mqtt` |
| `PAYMENT_CALLBACK_TOKEN` | 支付回调兼容 token | `replace-with-provider-secret` |
| `PAYMENT_SIGNING_SECRET` | 支付回调 HMAC 签名密钥 | `replace-with-payment-signing-secret` |
| `ADMIN_USERNAME` | 初始化管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 初始化管理员密码 | `123456` |

## 安全与一致性设计

- 用户鉴权：JWT access token + refresh token。
- 权限控制：RBAC，`admin > operator > user/device`。
- 设备鉴权：设备 SN + 一次性返回的设备密钥，服务端保存 hash。
- 支付回调：优先校验签名，兼容 `PAYMENT_CALLBACK_TOKEN`。
- 幂等：订单创建和支付回调支持 `Idempotency-Key`。
- 并发一致性：订单状态更新使用行锁。
- 异步可靠性：支付成功先写 outbox，再由 worker 调度业务任务。
- 失败处理：outbox 和设备命令链路保留 retry count、错误信息和死信表。

## 当前限制

- 支付回调仍是预留实现，真实微信支付/支付宝验签需要接入 `PaymentService.handle_callback` 和 `payment_signing.py`。
- 服务化入口共享同一个数据库和代码库，尚未做物理拆库拆仓。
- 遥测目前写入普通 PostgreSQL 表 `telemetry_points`，高频数据可后续替换为 TimescaleDB 或 InfluxDB。
- ESP32 示例仅有基础骨架，尚未实现 Wi-Fi、MQTT 订阅和 HTTP ACK。
- 容器中的 Celery worker 当前可能以 root 用户运行，生产部署应改为非 root 用户。

## 常用排障

查看 API 日志：

```bash
docker compose -f docker/docker-compose.yml logs -f backend
```

查看 worker 日志：

```bash
docker compose -f docker/docker-compose.yml logs -f worker
```

查看 RabbitMQ、Redis、PostgreSQL 健康状态：

```bash
docker compose -f docker/docker-compose.yml ps rabbitmq redis postgres
```

进入数据库：

```bash
docker compose -f docker/docker-compose.yml exec postgres psql -U app -d app_db
```

查看迁移版本：

```bash
docker compose -f docker/docker-compose.yml exec backend alembic current
```
