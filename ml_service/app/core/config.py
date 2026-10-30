
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ML_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "ML Service"
    app_version: str = "1.0.0"

    models_dir: Path = BASE_DIR / "models"
    data_dir: Path = BASE_DIR / "data"

    random_state: int = 42
    test_size: float = 0.2

    roc_auc_threshold: float = 0.80
    f1_threshold: float = 0.75
    accuracy_threshold: float = 0.78


settings = Settings()