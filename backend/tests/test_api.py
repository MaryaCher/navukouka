from unittest.mock import AsyncMock, patch
import pandas as pd
import io
from app.db.models import ModelVersion


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login(client):
    # Регистрация
    response = client.post("/api/auth/register", json={
        "username": "newuser", "password": "strong_password123"
    })
    assert response.status_code == 201

    # Логин
    response = client.post("/api/auth/login", json={
        "username": "newuser", "password": "strong_password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_get_me(client, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


@patch("app.api.routes.get_prediction", new_callable=AsyncMock)
def test_predict_success(mock_get_prediction, client, auth_headers, test_user):
    # Мокаем ответ от ML-сервиса
    mock_get_prediction.return_value = {
        "probability": 0.85, "probability_percent": 85.0,
        "prediction": 1, "threshold": 0.5, "model_id": "test_model"
    }

    response = client.post("/api/predict", json={
        "user_data": {"age": 25, "income": 50000}
    }, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["probability"] == 0.85


@patch("app.api.routes.call_training_service", new_callable=AsyncMock)
def test_train_model(mock_train, client, auth_headers):
    # Мокаем обучение
    mock_train.return_value = {
        "model_id": "new_model_123",
        "target_column": "target",
        "features": ["age"],
        "categorical_features": [],
        "metrics": {"accuracy": 0.9},
        "feature_importance": {"age": 0.5},
        "model_accepted": True,
        "threshold": 0.5
    }

    # Создаем фейковый CSV
    csv_content = "age,target\n25,1\n30,0"
    file = ("data.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")

    response = client.post("/api/models/train",
                           files={"file": file},
                           data={"target_column": "target"},
                           headers=auth_headers
                           )

    assert response.status_code == 200
    assert response.json()["model_id"] == "new_model_123"


def test_list_models(client, auth_headers, db_session, test_user):
    model = ModelVersion(
        version="v1", metrics={"acc": 0.9}, user_id=test_user.id, status="ready"
    )
    db_session.add(model)
    db_session.commit()

    response = client.get("/api/models", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_models_metrics(client, auth_headers, db_session, test_user):
    model = ModelVersion(
        version="v1", metrics={"acc": 0.9}, user_id=test_user.id, status="ready"
    )
    db_session.add(model)
    db_session.commit()

    response = client.get(f"/api/models/{model.id}/metrics", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["metrics"]["acc"] == 0.9


def test_prediction_history(client, auth_headers):
    response = client.get("/api/predictions/history", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()


@patch("app.api.routes.predict_batch", new_callable=AsyncMock)
def test_batch_predict(mock_predict_batch, client, auth_headers, db_session, test_user):
    # Мокаем пакетный прогноз
    mock_predict_batch.return_value = {
        "total_records": 2,
        "results": [
            {"probability": 0.8, "prediction": 1, "model_id": "v1"},
            {"probability": 0.2, "prediction": 0, "model_id": "v1"}
        ]
    }

    # Создаем фейковый CSV
    csv_content = "age,income\n25,50000\n30,60000"
    file = ("batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")

    response = client.post("/api/predictions/batch",
                           files={"file": file},
                           headers=auth_headers
                           )

    assert response.status_code == 200
    assert response.json()["successful_records"] == 2

# --- Тесты на ошибки и граничные случаи для routes.py ---

def test_register_duplicate_user(client, test_user):
    """Проверка ошибки 409 при дубликате"""
    response = client.post("/api/auth/register", json={
        "username": "testuser",  # уже существует
        "password": "strong_password123"
    })
    assert response.status_code == 409

def test_login_wrong_password(client, test_user):
    """Проверка ошибки 401"""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrong_password"
    })
    assert response.status_code == 401

@patch("app.api.routes.get_prediction", new_callable=AsyncMock)
def test_predict_ml_error(mock_get_prediction, client, auth_headers):
    """Проверка ошибки 503, если ML-сервис упал"""
    mock_get_prediction.side_effect = RuntimeError("ML упал")
    response = client.post("/api/predict", json={"user_data": {}}, headers=auth_headers)
    assert response.status_code == 503

def test_train_wrong_file_extension(client, auth_headers):
    """Проверка ошибки 400 при загрузке не CSV"""
    file = ("data.txt", io.BytesIO(b"test"), "text/plain")
    response = client.post("/api/models/train", files={"file": file}, data={"target_column": "target"}, headers=auth_headers)
    assert response.status_code == 400

def test_batch_predict_wrong_file(client, auth_headers):
    """Проверка ошибки 400 при загрузке не CSV в batch"""
    file = ("data.txt", io.BytesIO(b"test"), "text/plain")
    response = client.post("/api/predictions/batch", files={"file": file}, headers=auth_headers)
    assert response.status_code == 400

def test_get_metrics_not_found(client, auth_headers):
    """Проверка 404, если модель не найдена"""
    response = client.get("/api/models/9999/metrics", headers=auth_headers)
    assert response.status_code == 404

@patch("app.api.routes.predict_batch", new_callable=AsyncMock)
def test_batch_predict_empty_csv(mock_predict, client, auth_headers):
    """Ошибка 422 при пустом CSV"""
    file = ("empty.csv", io.BytesIO(b""), "text/csv")
    response = client.post("/api/predictions/batch", files={"file": file}, headers=auth_headers)
    assert response.status_code == 422

@patch("app.api.routes.predict_batch", new_callable=AsyncMock)
def test_batch_predict_ml_error(mock_predict, client, auth_headers):
    """Ошибка 503, если ML-сервис упал при batch"""
    mock_predict.side_effect = RuntimeError("ML down")
    csv_content = "age\n25"
    file = ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")
    response = client.post("/api/predictions/batch", files={"file": file}, headers=auth_headers)
    assert response.status_code == 503

@patch("app.api.routes.predict_batch", new_callable=AsyncMock)
def test_batch_predict_different_models(mock_predict, client, auth_headers):
    """Ошибка 502, если ML вернул результаты от разных моделей"""
    mock_predict.return_value = {
        "results": [
            {"probability": 0.5, "prediction": 1, "model_id": "model_A"},
            {"probability": 0.5, "prediction": 1, "model_id": "model_B"}
        ]
    }
    csv_content = "age\n25\n30"
    file = ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")
    response = client.post("/api/predictions/batch", files={"file": file}, headers=auth_headers)
    assert response.status_code == 502

def test_history_invalid_pagination(client, auth_headers):
    """Ошибка 422 при неверном лимите"""
    response = client.get("/api/predictions/history?limit=1000", headers=auth_headers)
    assert response.status_code == 422
