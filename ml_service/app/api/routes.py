
from io import BytesIO
from typing import Any
from pydantic import BaseModel
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.services.prediction_service import PredictionService
from app.services.training_service import TrainingService
from app.services.validation_service import DatasetValidationError

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ


class PredictionRequest(BaseModel):
    user_data: dict[str, Any]
class BatchPredictionRequest(BaseModel):
    records: list[dict[str, Any]]

@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ML Service"}


@router.post("/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:
    try:
        service = PredictionService()
        return service.predict(request.user_data)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Модель не найдена. Сначала необходимо обучить модель.",
        ) from error


@router.post("/train")
async def train_model(
    file: UploadFile = File(..., description="CSV-файл с историческими данными"),
    target_column: str = Form(..., description="Название целевой переменной"),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Загрузите файл с расширением .csv.",
        )

    try:
        contents = await file.read(MAX_FILE_SIZE + 1)

        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Размер CSV-файла не должен превышать 20 МБ.",
            )

        if not contents:
            raise HTTPException(
                status_code=422,
                detail="Загруженный файл пуст.",
            )

        dataframe = pd.read_csv(BytesIO(contents), encoding="utf-8-sig")

        service = TrainingService()
        return service.train(dataframe, target_column.strip())

    except HTTPException:
        raise
    except DatasetValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise HTTPException(
            status_code=422,
            detail="Не удалось прочитать CSV-файл. Проверьте его кодировку и формат.",
        ) from error
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        await file.close()


@router.post("/predict/batch")
def predict_batch(request: BatchPredictionRequest) -> dict[str, Any]:
    if not request.records:
        raise HTTPException(
            status_code=422,
            detail="Список записей для прогнозирования пуст.",
        )

    if len(request.records) > 1000:
        raise HTTPException(
            status_code=422,
            detail="За один запрос можно обработать не более 1000 записей.",
        )

    try:
        service = PredictionService()
        results = [
            service.predict(record)
            for record in request.records
        ]
        return {
            "total_records": len(results),
            "results": results,
        }
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Модель не найдена. Сначала необходимо обучить и сохранить модель.",
        ) from error