
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Интеллектуальный микросервис прогнозирования вероятности совершения целевого действия.",
)

app.include_router(router, prefix="/api")