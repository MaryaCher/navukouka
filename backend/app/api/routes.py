from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from app.schemas.training import ModelListItem, ModelListResponse
from app.core.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token
from app.db.database import get_db
from app.db.models import Role, User, PredictionHistory, ModelVersion
from app.schemas.training import TrainingResponse
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
)
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.ml_client import get_prediction
from app.services.training_client import train_model as call_training_service
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionHistoryItem,
    PredictionHistoryResponse,
    BatchPredictionResponse
)
from io import BytesIO

import pandas as pd

from app.db.models import PredictionBatch
from app.services.batch_prediction_client import predict_batch

BASE_STORAGE_DIR = Path("storage")
MODEL_STORAGE_DIR = BASE_STORAGE_DIR / "models"

router = APIRouter()

@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "Backend Service",
    }


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    existing_user = db.scalar(
        select(User).where(User.username == data.username)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Это имя пользователя уже занято",
        )

    user_role = db.scalar(
        select(Role).where(Role.name == "user")
    )

    if user_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Роль user не найдена в базе данных",
        )

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role_id=user_role.id,
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось зарегистрировать пользователя",
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user_role.name,
        is_active=user.is_active,
    )


@router.post(
    "/auth/login",
    response_model=TokenResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(
        select(User)
        .options(joinedload(User.role))
        .where(User.username == data.username)
    )

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись заблокирована",
        )

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/auth/me",
    response_model=UserResponse,
)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.name,
        is_active=current_user.is_active,
    )



@router.post(
    "/predict",
    response_model=PredictionResponse,
)
async def predict(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    try:
        result = await get_prediction(request.user_data)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    # Находим запись модели, которую использовал ML-сервис.
    model_version_id = None
    model_id = result.get("model_id")

    if model_id is not None:
        model_record = db.scalar(
            select(ModelVersion).where(
                ModelVersion.version == str(model_id)
            )
        )

        if model_record is not None:
            model_version_id = model_record.id

    history = PredictionHistory(
        user_id=current_user.id,
        model_version_id=model_version_id,
        input_data=request.user_data,
        probability=float(result["probability"]),
        prediction=int(result["prediction"]),
    )

    try:
        db.add(history)
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить историю прогноза",
        ) from error

    return PredictionResponse(
        probability=float(result["probability"]),
        probability_percent=float(result["probability_percent"]),
        prediction=int(result["prediction"]),
        threshold=float(result["threshold"]),
    )



@router.post("/models/train", response_model=TrainingResponse)
async def train_user_model(
    file: UploadFile = File(..., description="CSV-файл с историческими данными"),
    target_column: str = Form(..., description="Название целевой переменной"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(
            status_code=400,
            detail="Загрузите файл с расширением .csv.",
        )

    try:
        contents = await file.read(20 * 1024 * 1024 + 1)

        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="Размер CSV-файла не должен превышать 20 МБ.",
            )

        if not contents:
            raise HTTPException(
                status_code=422,
                detail="Загруженный файл пуст.",
            )

        result = await call_training_service(
            file_name=Path(file.filename).name,
            file_content=contents,
            target_column=target_column.strip(),
        )

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    finally:
        await file.close()

    database_model_id = None

    if result.get("model_accepted"):
        model_id = str(result["model_id"])

        model_dir = MODEL_STORAGE_DIR / model_id
        dataset_path = model_dir / "training_data.csv"

        try:
            # Создаём папку конкретной модели.
            model_dir.mkdir(parents=True, exist_ok=True)

            # Сохраняем исходный CSV, на котором обучалась модель.
            dataset_path.write_bytes(contents)

            record = ModelVersion(
                version=model_id,
                metrics=result["metrics"],
                user_id=current_user.id,
                model_path=f"models/{model_id}/model.cbm",
                dataset_path=f"storage/models/{model_id}/training_data.csv",
                target_column=result["target_column"],
                status="ready",
            )

            db.add(record)
            db.commit()
            db.refresh(record)

            database_model_id = record.id

        except Exception as error:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Модель обучена, но не удалось сохранить "
                    "обучающий датасет или сведения о модели."
                ),
            ) from error

    message = (
        "Модель обучена, прошла критерии качества и зарегистрирована в базе данных."
        if result.get("model_accepted")
        else (
            "Модель обучена, но не прошла установленные критерии качества. "
            "Она не сохранена и не зарегистрирована как готовая."
        )
    )

    return {
        **result,
        "database_model_id": database_model_id,
        "message": message,
    }


@router.get("/models", response_model=ModelListResponse)
def list_my_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(ModelVersion)
        .filter(ModelVersion.user_id == current_user.id)
        .order_by(ModelVersion.created_at.desc())
        .all()
    )

    items = [
        ModelListItem(
            id=record.id,
            version=record.version,
            metrics=record.metrics,
            target_column=record.target_column,
            status=record.status,
            created_at=record.created_at.isoformat(),
        )
        for record in records
    ]

    return ModelListResponse(items=items, total=len(items))


@router.get("/models/{model_db_id}/metrics")
def get_model_metrics(
    model_db_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.id == model_db_id,
            ModelVersion.user_id == current_user.id,
        )
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Модель не найдена.",
        )

    return {
        "id": record.id,
        "version": record.version,
        "target_column": record.target_column,
        "status": record.status,
        "metrics": record.metrics,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/predictions/history", response_model=PredictionHistoryResponse)
def get_prediction_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422,
            detail="Параметр limit должен быть от 1 до 100.",
        )

    if offset < 0:
        raise HTTPException(
            status_code=422,
            detail="Параметр offset не может быть отрицательным.",
        )

    query = db.query(PredictionHistory).filter(
        PredictionHistory.user_id == current_user.id
    )

    total = query.count()

    records = (
        query.order_by(PredictionHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        PredictionHistoryItem(
            id=record.id,
            input_data=record.input_data,
            probability=record.probability,
            prediction=record.prediction,
            model_version_id=record.model_version_id,
            batch_id=record.batch_id,
            created_at=record.created_at.isoformat(),
        )
        for record in records
    ]

    return PredictionHistoryResponse(items=items, total=total)

@router.post(
    "/predictions/batch",
    response_model=BatchPredictionResponse,
)
async def create_batch_prediction(
    file: UploadFile = File(
        ...,
        description="CSV-файл с данными пользователей",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Загрузите файл с расширением .csv.",
        )

    try:
        contents = await file.read(20 * 1024 * 1024 + 1)

        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="Размер CSV-файла не должен превышать 20 МБ.",
            )

        if not contents:
            raise HTTPException(
                status_code=422,
                detail="Загруженный файл пуст.",
            )

        try:
            dataframe = pd.read_csv(
                BytesIO(contents),
                encoding="utf-8-sig",
            )
        except (
            UnicodeDecodeError,
            pd.errors.ParserError,
            pd.errors.EmptyDataError,
        ) as error:
            raise HTTPException(
                status_code=422,
                detail="Не удалось прочитать CSV-файл.",
            ) from error

        if dataframe.empty:
            raise HTTPException(
                status_code=422,
                detail="CSV-файл не содержит записей.",
            )

        if len(dataframe) > 1000:
            raise HTTPException(
                status_code=422,
                detail="За один запрос можно обработать не более 1000 записей.",
            )

        dataframe = dataframe.where(pd.notna(dataframe), None)

        records = dataframe.to_dict(orient="records")

        batch = PredictionBatch(
            user_id=current_user.id,
            status="processing",
            total_records=len(records),
            successful_records=0,
            failed_records=0,
        )

        db.add(batch)
        db.commit()
        db.refresh(batch)

        try:
            ml_result = await predict_batch(records)
        except ValueError as error:
            batch.status = "failed"
            batch.failed_records = len(records)
            db.commit()

            raise HTTPException(
                status_code=422,
                detail=str(error),
            ) from error
        except RuntimeError as error:
            batch.status = "failed"
            batch.failed_records = len(records)
            db.commit()

            raise HTTPException(
                status_code=503,
                detail=str(error),
            ) from error

        results = ml_result.get("results", [])
        model_ids = {
            str(result["model_id"])
            for result in results
            if result.get("model_id") is not None
        }

        if len(model_ids) > 1:
            batch.status = "failed"
            batch.failed_records = len(records)
            db.commit()

            raise HTTPException(
                status_code=502,
                detail="ML-сервис использовал разные версии модели в одном пакете.",
            )

        model_version_id = None

        if model_ids:
            model_id = next(iter(model_ids))

            model_record = db.scalar(
                select(ModelVersion).where(
                    ModelVersion.version == model_id
                )
            )

            if model_record is not None:
                model_version_id = model_record.id

        batch.model_version_id = model_version_id
        if len(results) != len(records):
            batch.status = "failed"
            batch.failed_records = len(records)
            db.commit()

            raise HTTPException(
                status_code=502,
                detail="ML-сервис вернул некорректное количество результатов.",
            )

        # Добавляем исходные данные CSV к каждому результату
        enriched_results = []

        for input_data, result in zip(records, results):
            enriched_result = {
                **result,
                "input_data": input_data,
            }
            enriched_results.append(enriched_result)

        history_records = []

        for input_data, result in zip(records, results):
            history_records.append(
                PredictionHistory(
                    user_id=current_user.id,
                    model_version_id=model_version_id,
                    batch_id=batch.id,
                    input_data=input_data,
                    probability=float(result["probability"]),
                    prediction=int(result["prediction"]),
                )
            )

        db.add_all(history_records)

        batch.status = "completed"
        batch.successful_records = len(history_records)
        batch.failed_records = 0

        db.commit()

        return BatchPredictionResponse(
            batch_id=batch.id,
            status=batch.status,
            total_records=batch.total_records,
            successful_records=batch.successful_records,
            failed_records=batch.failed_records,
            results=enriched_results,
        )

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Не удалось выполнить массовое прогнозирование.",
        ) from error

    finally:
        await file.close()