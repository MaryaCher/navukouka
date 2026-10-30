
import pandas as pd


class DatasetValidationError(Exception):
    """Ошибка проверки входного датасета."""


def validate_training_dataset(
    dataframe: pd.DataFrame,
    target_column: str,
) -> None:
    """Проверяет данные перед обучением модели."""

    if dataframe.empty:
        raise DatasetValidationError(
            "Загруженный датасет не содержит записей."
        )

    if target_column not in dataframe.columns:
        raise DatasetValidationError(
            f"Целевая переменная '{target_column}' "
            "отсутствует в датасете."
        )

    feature_columns = [
        column
        for column in dataframe.columns
        if column != target_column
    ]

    if not feature_columns:
        raise DatasetValidationError(
            "Датасет должен содержать хотя бы один признак."
        )

    if len(dataframe) < 100:
        raise DatasetValidationError(
            "Для обучения требуется не менее 100 записей."
        )

    if dataframe[target_column].isna().any():
        raise DatasetValidationError(
            "Целевая переменная содержит пропущенные значения."
        )

    target_values = dataframe[target_column].unique()

    if len(target_values) != 2:
        raise DatasetValidationError(
            "Целевая переменная должна содержать ровно два класса."
        )


def validate_prediction_dataset(
    dataframe: pd.DataFrame,
    required_features: list[str],
) -> None:
    """Проверяет данные перед прогнозированием."""

    if dataframe.empty:
        raise DatasetValidationError(
            "Датасет для прогнозирования не содержит записей."
        )

    missing_features = [
        feature
        for feature in required_features
        if feature not in dataframe.columns
    ]

    if missing_features:
        raise DatasetValidationError(
            "В датасете отсутствуют необходимые признаки: "
            + ", ".join(missing_features)
        )