from typing import Any

from pydantic import BaseModel


class TrainingResponse(BaseModel):
    model_id: str

    target_column: str

    features: list[str]

    numerical_features: list[str]

    categorical_features: list[str]

    class_mapping: dict[str, int]

    positive_class: str

    metrics: dict[str, Any]

    feature_importance: dict[str, float]

    best_parameters: dict[str, Any]

    model_accepted: bool

    threshold: float

    quality_requirements: dict[str, float]


class PredictionResponse(BaseModel):
    model_id: str

    probability: float

    probability_percent: float

    prediction: int

    predicted_label: str

    threshold: float


class ModelInfo(BaseModel):
    model_id: str

    target_column: str

    features: list[str]

    numerical_features: list[str]

    categorical_features: list[str]

    metrics: dict[str, Any]

    model_accepted: bool

    best_parameters: dict[str, Any]