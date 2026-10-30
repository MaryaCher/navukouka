
import httpx

from app.core.config import settings


async def predict_batch(records: list[dict]) -> dict:
    url = f"{settings.ml_service_url.rstrip('/')}/api/predict/batch"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                json={"records": records},
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as error:
        if error.response.status_code == 422:
            try:
                detail = error.response.json().get(
                    "detail", "Некорректные данные для прогнозирования."
                )
            except ValueError:
                detail = "Некорректные данные для прогнозирования."

            raise ValueError(str(detail)) from error

        if error.response.status_code == 503:
            raise RuntimeError(
                "Нет доступной сохранённой модели для прогнозирования."
            ) from error

        raise RuntimeError(
            f"ML-сервис вернул HTTP {error.response.status_code}."
        ) from error

    except httpx.RequestError as error:
        raise RuntimeError(
            "Не удалось подключиться к ML-микросервису."
        ) from error