
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from app.ml.evaluator import evaluate_model


class ModelTrainer:
    def __init__(
        self,
        random_state: int = 42,
        test_size: float = 0.2,
    ) -> None:
        if not 0 < test_size < 0.5:
            raise ValueError(
                "test_size должен быть больше 0 и меньше 0.5."
            )

        self.random_state = random_state
        self.test_size = test_size

    def _detect_feature_types(
        self,
        dataframe: pd.DataFrame,
        target_column: str,
    ) -> tuple[list[str], list[str]]:
        numerical_features = []
        categorical_features = []

        for column in dataframe.columns:
            if column == target_column:
                continue

            series = dataframe[column]

            if pd.api.types.is_bool_dtype(series):
                categorical_features.append(column)
            elif pd.api.types.is_numeric_dtype(series):
                numerical_features.append(column)
            else:
                converted = pd.to_numeric(
                    series,
                    errors="coerce",
                )

                if converted.notna().mean() >= 0.95:
                    numerical_features.append(column)
                else:
                    categorical_features.append(column)

        return numerical_features, categorical_features

    def _preprocess_features(
        self,
        dataframe: pd.DataFrame,
        numerical_features: list[str],
        categorical_features: list[str],
    ) -> pd.DataFrame:
        dataframe = dataframe.copy()

        for column in numerical_features:
            dataframe[column] = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )

            median = dataframe[column].median()

            if pd.isna(median):
                median = 0.0

            dataframe[column] = dataframe[column].fillna(
                median
            )

        for column in categorical_features:
            dataframe[column] = (
                dataframe[column]
                .astype("string")
                .fillna("__MISSING__")
                .astype(str)
            )

        return dataframe

    def _find_best_parameters(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        categorical_features: list[int],
    ) -> dict[str, Any]:
        candidates = [
            {
                "iterations": 300,
                "depth": 4,
                "learning_rate": 0.05,
                "l2_leaf_reg": 3,
            },
            {
                "iterations": 500,
                "depth": 4,
                "learning_rate": 0.03,
                "l2_leaf_reg": 5,
            },
            {
                "iterations": 300,
                "depth": 5,
                "learning_rate": 0.05,
                "l2_leaf_reg": 3,
            },
            {
                "iterations": 500,
                "depth": 5,
                "learning_rate": 0.03,
                "l2_leaf_reg": 5,
            },
            {
                "iterations": 500,
                "depth": 6,
                "learning_rate": 0.05,
                "l2_leaf_reg": 3,
            },
            {
                "iterations": 700,
                "depth": 6,
                "learning_rate": 0.03,
                "l2_leaf_reg": 5,
            },
            {
                "iterations": 500,
                "depth": 7,
                "learning_rate": 0.03,
                "l2_leaf_reg": 5,
            },
        ]

        if len(X_train) < 50:
            return candidates[0]

        try:
            X_subtrain, X_validation, y_subtrain, y_validation = (
                train_test_split(
                    X_train,
                    y_train,
                    test_size=0.2,
                    random_state=self.random_state,
                    stratify=y_train,
                )
            )
        except ValueError:
            return candidates[0]

        best_parameters = candidates[0]
        best_auc = -1.0

        for parameters in candidates:
            model = CatBoostClassifier(
                **parameters,
                loss_function="Logloss",
                eval_metric="AUC",
                random_seed=self.random_state,
                verbose=False,
                allow_writing_files=False,
                thread_count=-1,
            )

            model.fit(
                X_subtrain,
                y_subtrain,
                cat_features=categorical_features,
                verbose=False,
            )

            probabilities = model.predict_proba(
                X_validation
            )[:, 1]

            metrics = evaluate_model(
                y_validation,
                probabilities,
            )

            auc = metrics["roc_auc"]

            if auc is not None and auc > best_auc:
                best_auc = auc
                best_parameters = parameters

        return best_parameters

    @staticmethod
    def _find_best_threshold(
        y_true: pd.Series,
        probabilities: np.ndarray,
    ) -> float:
        """Подбирает порог по Accuracy на валидационной выборке."""
        thresholds = np.arange(0.20, 0.801, 0.01)

        best_threshold = 0.5
        best_accuracy = -1.0

        for threshold in thresholds:
            predictions = (
                probabilities >= threshold
            ).astype(int)

            accuracy = accuracy_score(
                y_true,
                predictions,
            )

            # При равной Accuracy предпочитаем порог,
            # который ближе к стандартному значению 0.5.
            if (
                accuracy > best_accuracy
                or (
                    np.isclose(accuracy, best_accuracy)
                    and abs(threshold - 0.5)
                    < abs(best_threshold - 0.5)
                )
            ):
                best_accuracy = float(accuracy)
                best_threshold = float(threshold)

        return best_threshold

    def train(
        self,
        dataframe: pd.DataFrame,
        target_column: str,
    ) -> dict[str, Any]:
        if dataframe.empty:
            raise ValueError("Датасет пуст.")

        if target_column not in dataframe.columns:
            raise ValueError(
                f"Целевая колонка '{target_column}' не найдена."
            )

        if dataframe[target_column].isna().any():
            raise ValueError(
                "Целевая колонка содержит пропуски."
            )

        X = dataframe.drop(
            columns=[target_column]
        ).copy()

        y_original = dataframe[target_column].copy()

        if X.shape[1] == 0:
            raise ValueError("Нет признаков для обучения.")

        empty_columns = [
            column
            for column in X.columns
            if X[column].isna().all()
        ]

        if empty_columns:
            raise ValueError(
                "Следующие признаки полностью пустые: "
                + ", ".join(empty_columns)
            )

        classes = sorted(
            y_original.unique().tolist(),
            key=lambda value: str(value),
        )

        if len(classes) != 2:
            raise ValueError(
                "Целевая колонка должна содержать ровно два класса."
            )

        class_mapping = {
            classes[0]: 0,
            classes[1]: 1,
        }

        y = y_original.map(class_mapping).astype(int)

        if int(y.value_counts().min()) < 3:
            raise ValueError(
                "В каждом классе должно быть не менее трёх записей."
            )

        numerical_features, categorical_features = (
            self._detect_feature_types(
                dataframe,
                target_column,
            )
        )

        X = self._preprocess_features(
            X,
            numerical_features,
            categorical_features,
        )

        categorical_indices = [
            X.columns.get_loc(column)
            for column in categorical_features
        ]

        X_train_val, X_test, y_train_val, y_test = (
            train_test_split(
                X,
                y,
                test_size=self.test_size,
                random_state=self.random_state,
                stratify=y,
            )
        )

        best_parameters = self._find_best_parameters(
            X_train_val,
            y_train_val,
            categorical_indices,
        )

        X_train, X_validation, y_train, y_validation = (
            train_test_split(
                X_train_val,
                y_train_val,
                test_size=0.2,
                random_state=self.random_state,
                stratify=y_train_val,
            )
        )

        model = CatBoostClassifier(
            **best_parameters,
            loss_function="Logloss",
            eval_metric="AUC",
            random_seed=self.random_state,
            verbose=False,
            allow_writing_files=False,
            thread_count=-1,
        )

        model.fit(
            X_train,
            y_train,
            cat_features=categorical_indices,
            eval_set=(X_validation, y_validation),
            early_stopping_rounds=50,
            verbose=False,
        )

        # Сначала выбираем порог исключительно на validation.
        validation_probabilities = model.predict_proba(
            X_validation
        )[:, 1]

        best_threshold = self._find_best_threshold(
            y_validation,
            validation_probabilities,
        )

        # Тестовую выборку используем только для оценки.
        test_probabilities = model.predict_proba(
            X_test
        )[:, 1]

        metrics_default = evaluate_model(
            y_test,
            test_probabilities,
            threshold=0.5,
        )

        metrics_tuned = evaluate_model(
            y_test,
            test_probabilities,
            threshold=best_threshold,
        )

        feature_importance = {
            str(feature): float(importance)
            for feature, importance in zip(
                X.columns,
                model.get_feature_importance(),
            )
        }

        return {
            "model": model,
            "metrics": metrics_tuned,
            "metrics_default_threshold": metrics_default,
            "threshold": best_threshold,
            "feature_importance": feature_importance,
            "features": list(X.columns),
            "numerical_features": numerical_features,
            "categorical_features": categorical_features,
            "best_parameters": best_parameters,
            "class_mapping": {
                str(label): encoded
                for label, encoded in class_mapping.items()
            },
            "positive_class": str(classes[1]),
        }
