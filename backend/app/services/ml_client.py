import httpx

from app.core.config import settings


async def get_prediction(features: dict) -> dict:
    url = f"{settings.ml_service_url.rstrip('/')}/api/predict"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"user_data": features},
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"ML-сервис вернул HTTP {exc.response.status_code}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            "Не удалось подключиться к ML-сервису"
        ) from exc