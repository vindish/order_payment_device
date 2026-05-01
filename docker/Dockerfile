FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y gcc

# 复制依赖
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY backend .

# 启动
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
