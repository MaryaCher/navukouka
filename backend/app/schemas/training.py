
from typing import Any

from pydantic import BaseModel


class TrainingResponse(BaseModel):
    model_id: str
    target_column: str
    features: list[str]
    categorical_features: list[str]
    metrics: dict[str, Any]
    feature_importance: dict[str, float]
    model_accepted: bool
    threshold: float
    database_model_id: int | None = None
    message: str


class ModelListItem(BaseModel):
    id: int
    version: str
    metrics: dict[str, Any]
    target_column: str | None
    status: str
    created_at: str


class ModelListResponse(BaseModel):
    items: list[ModelListItem]
    total: int