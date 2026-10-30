
import httpx

from app.core.config import settings


async def train_model(
    file_name: str,
    file_content: bytes,
    target_column: str,
) -> dict:
    url = f"{settings.ml_service_url.rstrip('/')}/api/train"

    files = {
        "file": (
            file_name,
            file_content,
            "text/csv",
        )
    }
    data = {
        "target_column": target_column,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                url,
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (400, 413, 422):
            try:
                detail = exc.response.json().get(
                    "detail",
                    "Ошибка проверки файла или данных",
                )
            except ValueError:
                detail = "Ошибка проверки файла или данных"

            raise ValueError(str(detail)) from exc

        raise RuntimeError(
            f"ML-сервис вернул HTTP {exc.response.status_code}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            "Не удалось подключиться к ML-микросервису"
        ) from exc