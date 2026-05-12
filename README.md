# Order Payment Device

事件驱动的订单支付开锁系统，包含 FastAPI API、PostgreSQL、Alembic、Redis、Celery、MQTT、Next.js H5 前端和 ESP32 设备端示例。

## 生产结构

- API: `backend/app/main.py`
- 数据库迁移: `backend/alembic`
- 任务队列: Celery + Redis
- 设备通信: MQTT topic `device/{sn}/cmd`
- 前端: `frontend`，接口层位于 `frontend/lib`，可在微信小程序中复用接口定义并替换 `request` 实现
- Docker 编排: `docker/docker-compose.yml`

## 启动

```bash
docker compose -f docker/docker-compose.yml up --build
```

服务地址：

- API: `http://localhost:8000`
- API 文档: `http://localhost:8000/docs`
- 前端: `http://localhost:3000`
- MQTT: `localhost:1883`
- PostgreSQL: `localhost:5432`

默认会创建本地管理员：`admin / 123456`。生产环境请通过 `.env` 覆盖 `ADMIN_PASSWORD` 和 `SECRET_KEY`。

## 常用命令

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

## 回调预留

当前支付回调为预留接口：

`POST /api/v1/payments/callback`

```json
{
  "order_id": 1,
  "provider": "wechat",
  "trade_no": "provider-trade-no",
  "token": "replace-with-provider-secret"
}
```

真实微信支付/支付宝验签逻辑后续接入到 `PaymentService.handle_callback`。


# update


────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

• 已完成一轮大升级并试运行通过。

  主要补齐：

  - 安全：设备鉴权、支付签名/回调 token 兼容、JWT refresh token、RBAC。
  - 一致性：订单行锁、幂等键、outbox pattern、Celery retry、死信表。
  - 微服务化：新增 user-service/order-service/payment-service/device-service 独立 FastAPI 入口和 compose 服务。
  - 消息队列：新增 RabbitMQ，Celery broker 已从 Redis 切到 amqp://app:**@rabbitmq:5672//，Redis 保留作 result backend。
  - IoT 平台基础：设备密钥、心跳、影子、指令下发、ACK、遥测表、规则定义表、设备命令表。

  验证结果：

  - docker compose -f docker/docker-compose.yml up -d --build 已成功。
  - 所有容器 running/healthy：backend、frontend、4 个拆分服务、worker、scheduler、postgres、redis、mqtt、rabbitmq。
  - Health 全部通过：8000、8101、8102、8103、8104。
  - Alembic 当前版本：202605120002。
  - Worker 日志确认 RabbitMQ：transport: amqp://app:**@rabbitmq:5672//。
  - 支付链路已 smoke test：订单 PAID -> UNLOCKING，outbox PUBLISHED，设备 unlock 指令 SENT，死信为 0。
  - .dockerignore 仍生效，backend build context 维持几十 KB 级别。

  RabbitMQ 管理台现在在 http://localhost:15672，账号 app，密码 app123。

  注意：这版是“可运行的服务化基础版”，不是完全物理拆库/拆仓的最终形态；时序数据库目前用 telemetry_points 表承接，后续可替换 TimescaleDB/InfluxDB。Celery 仍有 root 运行
  warning，不影响功能，但生产部署应加非 root 用户。

─ Worked for 38m 22s ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────





# update
已修改并试运行通过。

  改动：

  - 新增 /home/uber/projects/.dockerignore，排除 backend/venv、__pycache__、本地 db、.next、node_modules 等。
  - 移除 /home/uber/projects/docker/docker-compose.yml 里的 obsolete version 字段。
  - 新增 /home/uber/projects/backend/app/scripts/prepare_migrations.py，用于兼容旧数据库已有表但 schema/Alembic 版本不完整的情况。
  - 更新 /home/uber/projects/docker/backend-entrypoint.sh，迁移前先执行兼容准备脚本。

  验证结果：

  - backend/worker build context 从之前约 97.97MB 降到几十 KB，后续 build 基本走缓存。
  - docker compose -f docker/docker-compose.yml up -d --build 已成功启动。
  - opd-api healthy，opd-frontend running，opd-worker running。
  - http://localhost:8000/health 返回：
    {"status":"ok","service":"Order Payment Device","env":"prod"}
  - http://localhost:3000 返回 200 OK。
  - 数据库 alembic_version 已是 202605120001，旧表缺失字段已补齐。

  剩余提示：worker 日志里还有 Celery 以 root 用户运行的安全 warning，不影响当前启动；后续可以单独加非 root 用户运行容器。当前 git 状态里 .vscode/ 是已有未跟踪项，我没有动它。