from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Device System"

    SECRET_KEY: str = "super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # DATABASE_URL: str = "sqlite:///./test.db"
    # DATABASE_URL =      "postgresql+psycopg2://app:app123@postgres:5432/app_db"W
    DATABASE_URL: str = "postgresql+psycopg2://app:app123@postgres:5432/app_db"

    # ✅ 新增
    REDIS_HOST: str = "localhost"
    MQTT_HOST: str = "localhost"

settings = Settings()