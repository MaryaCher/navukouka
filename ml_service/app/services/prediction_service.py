from typing import Any

import pandas as pd

from app.core.config import settings
from app.storage.model_storage import ModelStorage


class PredictionService:
    def __init__(
        self,
        model_id: str | None = None,
    ) -> None:
        self.storage = ModelStorage(
            settings.models_dir
        )

        self.model, self.metadata = (
            self.storage.load(
                model_id=model_id
            )
        )

    def predict(
        self,
        user_data: dict[str, Any],
    ) -> dict[str, Any]:
        features = self.metadata[
            "features"
        ]

        # -----------------------------------------------------
        # Проверяем обязательные признаки
        # -----------------------------------------------------

        missing_features = [
            feature
            for feature in features
            if feature not in user_data
        ]

        if missing_features:
            raise ValueError(
                "Не указаны обязательные признаки: "
                + ", ".join(missing_features)
            )

        # -----------------------------------------------------
        # Создаём DataFrame
        # -----------------------------------------------------

        dataframe = pd.DataFrame(
            [
                {
                    feature: user_data[feature]
                    for feature in features
                }
            ]
        )

        numerical_features = self.metadata.get(
            "numerical_features",
            [],
        )

        categorical_features = self.metadata.get(
            "categorical_features",
            [],
        )

        # -----------------------------------------------------
        # Обрабатываем числовые признаки
        # -----------------------------------------------------

        for feature in numerical_features:
            dataframe[feature] = pd.to_numeric(
                dataframe[feature],
                errors="coerce",
            )

            if dataframe[feature].isna().any():
                raise ValueError(
                    f"Признак '{feature}' должен "
                    "содержать числовое значение."
                )

        # -----------------------------------------------------
        # Обрабатываем категориальные признаки
        # -----------------------------------------------------

        for feature in categorical_features:
            dataframe[feature] = (
                dataframe[feature]
                .fillna("__MISSING__")
                .astype(str)
            )

        # -----------------------------------------------------
        # Prediction
        # -----------------------------------------------------

        probabilities = (
            self.model.predict_proba(
                dataframe
            )[0]
        )

        probability = float(
            probabilities[1]
        )

        threshold = float(
            self.metadata.get(
                "threshold",
                0.5,
            )
        )

        prediction = int(
            probability >= threshold
        )

        # -----------------------------------------------------
        # Определяем название класса
        # -----------------------------------------------------

        class_mapping = self.metadata.get(
            "class_mapping",
            {},
        )

        predicted_class = str(
            prediction
        )

        predicted_label = next(
            (
                label
                for label, encoded_value
                in class_mapping.items()
                if encoded_value == prediction
            ),
            predicted_class,
        )

        return {
            "model_id": self.metadata.get(
                "model_id"
            ),
            "probability": probability,
            "probability_percent": round(
                probability * 100,
                2,
            ),
            "prediction": prediction,
            "predicted_label": predicted_label,
            "threshold": threshold,
        }