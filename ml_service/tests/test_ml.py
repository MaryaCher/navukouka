import pytest
import pandas as pd
from app.ml.evaluator import evaluate_model
from fastapi.testclient import TestClient

from app.main import app
from app.ml.trainer import ModelTrainer
def test_evaluate_model_returns_metrics():
    y_true = [0, 0, 1, 1]
    probabilities = [0.1, 0.4, 0.7, 0.9]

    result = evaluate_model(y_true, probabilities)

    assert result["accuracy"] == 1.0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0
    assert result["roc_auc"] == 1.0
    assert result["confusion_matrix"] == [[2, 0], [0, 2]]


def test_evaluate_model_invalid_probability():
    with pytest.raises(ValueError):
        evaluate_model([0, 1], [0.2, 1.5])


def test_evaluate_model_mismatched_lengths():
    with pytest.raises(ValueError):
        evaluate_model([0, 1], [0.2])


def test_evaluate_model_empty_data():
    with pytest.raises(ValueError):
        evaluate_model([], [])

@pytest.fixture
def sample_dataset():
    # Искусственный датасет для проверки обучения.
    rows = []

    for i in range(120):
        age = 18 + (i % 50)
        income = 20000 + (i * 1500)
        region = ["Москва", "Казань", "Самара"][i % 3]
        target = int(age > 40 or income > 100000)

        rows.append({
            "age": age,
            "income": income,
            "region": region,
            "target": target,
        })

    return pd.DataFrame(rows)


def test_train_returns_model_and_metrics(sample_dataset):
    trainer = ModelTrainer(random_state=42, test_size=0.2)

    result = trainer.train(sample_dataset, "target")

    assert result["model"] is not None
    assert "accuracy" in result["metrics"]
    assert "precision" in result["metrics"]
    assert "recall" in result["metrics"]
    assert "f1" in result["metrics"]
    assert "roc_auc" in result["metrics"]
    assert "confusion_matrix" in result["metrics"]
    assert result["features"] == ["age", "income", "region"]
    assert "region" in result["categorical_features"]


def test_train_missing_target_column(sample_dataset):
    trainer = ModelTrainer()

    with pytest.raises(ValueError, match="не найдена"):
        trainer.train(sample_dataset, "missing_target")


def test_train_empty_dataset():
    trainer = ModelTrainer()

    with pytest.raises(ValueError, match="пуст"):
        trainer.train(pd.DataFrame(), "target")


def test_train_target_with_missing_values(sample_dataset):
    trainer = ModelTrainer()
    sample_dataset.loc[0, "target"] = None

    with pytest.raises(ValueError, match="пропуски"):
        trainer.train(sample_dataset, "target")


def test_train_target_with_one_class(sample_dataset):
    trainer = ModelTrainer()
    sample_dataset["target"] = 0

    with pytest.raises(ValueError, match="ровно два класса"):
        trainer.train(sample_dataset, "target")



client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ML Service",
    }


def test_openapi_schema():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "paths" in response.json()