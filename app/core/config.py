from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "CloudSales"
    DATABASE_URL: str = "postgresql://subscription_user:subscription_password@127.0.0.1:5432/subscription_db"

    class Config:
        env_file = ".env"


settings = Settings()
