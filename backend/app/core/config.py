from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Backend Service"
    app_version: str = "1.0.0"
    ml_service_url: str = "http://127.0.0.1:8000"
    database_url: str = (
        "mysql+pymysql://root:1234@127.0.0.1:3306/navukouka"
    )
    jwt_secret: str
    jwt_expire_minutes: int = 30

settings = Settings()