from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Device System"
    SECRET_KEY: str = "super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "sqlite:///./test.db"

settings = Settings()