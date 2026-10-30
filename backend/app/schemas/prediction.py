from typing import Any

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    user_data: dict[str, Any] = Field(
        ...,
        description="Признаки пользователя для ML-модели",
    )


class PredictionResponse(BaseModel):
    probability: float
    probability_percent: float
    prediction: int
    threshold: float


class PredictionHistoryItem(BaseModel):
    id: int
    input_data: dict[str, Any]
    probability: float
    prediction: int
    model_version_id: int | None
    batch_id: int | None
    created_at: str


class PredictionHistoryResponse(BaseModel):
    items: list[PredictionHistoryItem]
    total: int


class BatchPredictionResponse(BaseModel):
    batch_id: int
    status: str
    total_records: int
    successful_records: int
    failed_records: int
    results: list[dict[str, Any]]