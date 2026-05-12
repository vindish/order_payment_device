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
