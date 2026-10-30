import pytest
import pandas as pd
from unittest.mock import MagicMock
from app.services.validation_service import (
    validate_training_dataset,
    DatasetValidationError,
)
from app.services.prediction_service import PredictionService


# ============================================================
# ТЕСТЫ ВАЛИДАЦИИ ДАТАСЕТА (Пограничные кейсы)
# ============================================================

def test_empty_dataset_fails():
    df = pd.DataFrame()
    with pytest.raises(DatasetValidationError, match="не содержит записей"):
        validate_training_dataset(df, "target")


def test_missing_target_column_fails():
    df = pd.DataFrame({"age": [20, 30], "income": [100, 200]})
    with pytest.raises(DatasetValidationError, match="отсутствует в датасете"):
        validate_training_dataset(df, "target")


def test_too_few_records_fails():
    # Менее 100 записей
    df = pd.DataFrame({"age": range(50), "target": [0, 1] * 25})
    with pytest.raises(DatasetValidationError, match="не менее 100 записей"):
        validate_training_dataset(df, "target")


def test_missing_values_in_target_fails():
    # 100 записей, но в целевой переменной есть NaN
    df = pd.DataFrame({"age": range(100), "target": [0, 1] * 49 + [None, None]})
    with pytest.raises(DatasetValidationError, match="содержит пропущенные значения"):
        validate_training_dataset(df, "target")


def test_one_class_in_target_fails():
    # Все ответы только 1 (нет бинарности)
    df = pd.DataFrame({"age": range(100), "target": [1] * 100})
    with pytest.raises(DatasetValidationError, match="ровно два класса"):
        validate_training_dataset(df, "target")


# ============================================================
# ТЕСТЫ УСТОЙЧИВОСТИ ПРОГНОЗИРОВАНИЯ (Обработка аномалий)
# ============================================================

@pytest.fixture
def mock_prediction_service():
    """Создает сервис с фейковой моделью и метаданными"""
    service = PredictionService.__new__(PredictionService)  # Обходим __init__
    service.model = MagicMock()
    # Настраиваем, что модель возвращает вероятность 0.8
    service.model.predict_proba.return_value = [[0.2, 0.8]]

    service.metadata = {
        "features": ["age", "gender"],
        "numerical_features": ["age"],
        "categorical_features": ["gender"],
        "threshold": 0.5,
        "class_mapping": {"0": 0, "1": 1},
        "model_id": "test_model"
    }
    return service


def test_predict_missing_feature_fails(mock_prediction_service):
    """Если пользователь не передал обязательный признак"""
    user_data = {"age": 25}  # Нет gender
    with pytest.raises(ValueError, match="Не указаны обязательные признаки"):
        mock_prediction_service.predict(user_data)


def test_predict_invalid_numeric_value_fails(mock_prediction_service):
    """Если в числовой признак передали текст"""
    user_data = {"age": "двадцать пять", "gender": "M"}
    with pytest.raises(ValueError, match="должен содержать числовое значение"):
        mock_prediction_service.predict(user_data)


def test_predict_handles_missing_categorical(mock_prediction_service):
    """Если категориальный признак пустой (None), он должен замениться на __MISSING__"""
    user_data = {"age": 25, "gender": None}
    result = mock_prediction_service.predict(user_data)

    # Проверяем, что модель была вызвана с корректным DataFrame
    args, _ = mock_prediction_service.model.predict_proba.call_args
    passed_df = args[0]

    assert passed_df.iloc[0]["gender"] == "__MISSING__"
    assert result["prediction"] == 1
    assert result["probability"] == 0.8