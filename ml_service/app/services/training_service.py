from uuid import uuid4

import pandas as pd

from app.core.config import settings
from app.ml.trainer import ModelTrainer
from app.services.validation_service import validate_training_dataset
from app.storage.model_storage import ModelStorage


class TrainingService:
    def __init__(self) -> None:
        self.trainer = ModelTrainer(
            random_state=settings.random_state,
            test_size=settings.test_size,
        )

        self.storage = ModelStorage(
            settings.models_dir
        )

    def train(
        self,
        dataframe: pd.DataFrame,
        target_column: str,
    ) -> dict:
        # -----------------------------------------------------
        # 1. Проверяем датасет
        # -----------------------------------------------------

        validate_training_dataset(
            dataframe,
            target_column,
        )

        # -----------------------------------------------------
        # 2. Обучаем модель
        # -----------------------------------------------------

        result = self.trainer.train(
            dataframe,
            target_column,
        )

        metrics = result["metrics"]
        metrics_default = result["metrics_default_threshold"]

        roc_auc = metrics["roc_auc"]
        f1 = metrics["f1"]
        accuracy = metrics["accuracy"]

        model_accepted = (
                roc_auc is not None
                and roc_auc >= settings.roc_auc_threshold
                and f1 >= settings.f1_threshold
                and accuracy >= settings.accuracy_threshold
        )

        # -----------------------------------------------------
        # 4. Создаём ID модели
        # -----------------------------------------------------

        model_id = str(uuid4())

        # -----------------------------------------------------
        # 5. Формируем metadata
        # -----------------------------------------------------

        metadata = {
            "model_id": model_id,

            "target_column": target_column,

            "features": result["features"],

            "numerical_features": result[
                "numerical_features"
            ],

            "categorical_features": result[
                "categorical_features"
            ],

            "class_mapping": result[
                "class_mapping"
            ],

            "positive_class": result[
                "positive_class"
            ],

            "metrics": metrics,

            "feature_importance": result[
                "feature_importance"
            ],

            "best_parameters": result[
                "best_parameters"
            ],

            "model_accepted": model_accepted,

            "threshold": result["threshold"],

            "quality_requirements": {
                "roc_auc": settings.roc_auc_threshold,
                "f1": settings.f1_threshold,
                "accuracy": settings.accuracy_threshold,
            },
        }

        # -----------------------------------------------------
        # 6. Сохраняем модель только если качество достаточное
        # -----------------------------------------------------

        if model_accepted:
            self.storage.save(
                model=result["model"],
                metadata=metadata,
                model_id=model_id,
            )

        # -----------------------------------------------------
        # 7. Возвращаем результат API
        # -----------------------------------------------------

        return metadata