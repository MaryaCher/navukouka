import os
import tempfile
import pandas as pd
from app.db.models import ModelVersion


def test_analytics_endpoint(client, auth_headers, db_session, test_user):
    # Создаем временный CSV файл для модели
    df = pd.DataFrame({
        "age": [20, 30, 40, 50],
        "gender": ["M", "F", "M", "F"],
        "target": [1, 1, 0, 0]
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    try:
        # Создаем модель в БД с указанием пути к CSV
        model = ModelVersion(
            version="analytics_v1",
            metrics={"acc": 0.9},
            user_id=test_user.id,
            status="ready",
            target_column="target",
            dataset_path=tmp_path
        )
        db_session.add(model)
        db_session.commit()

        # Запрашиваем аналитику
        response = client.get(f"/api/models/{model.id}/analytics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "dataset" in data
        assert "features" in data
        assert "insights" in data
        assert data["dataset"]["rows"] == 4

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_analytics_model_not_found(client, auth_headers):
    """Проверка 404, если модели нет"""
    response = client.get("/api/models/9999/analytics", headers=auth_headers)
    assert response.status_code == 404


def test_analytics_no_dataset_path(client, auth_headers, db_session, test_user):
    """Проверка 404, если у модели нет датасета"""
    model = ModelVersion(
        version="no_dataset", metrics={}, user_id=test_user.id,
        status="ready", target_column="target", dataset_path=None
    )
    db_session.add(model)
    db_session.commit()

    response = client.get(f"/api/models/{model.id}/analytics", headers=auth_headers)
    assert response.status_code == 404


import pandas as pd
import os
import tempfile


def test_analytics_with_predictions_and_segments(client, auth_headers, db_session, test_user):
    """Тест покрывает анализ прогнозов, сегменты и инсайты"""
    from app.db.models import PredictionHistory

    # 1. Создаем CSV с категориальными и числовыми признаками
    df = pd.DataFrame({
        "age": [20, 30, 40, 50, 20, 30, 40, 50, 20, 30],
        "gender": ["M", "F", "M", "F", "M", "F", "M", "F", "M", "F"],
        "education": ["High", "Low", "High", "Low", "High", "Low", "High", "Low", "High", "Low"],
        "target": [1, 1, 0, 0, 1, 1, 0, 0, 1, 1]
    })

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    try:
        model = ModelVersion(
            version="analytics_full", metrics={}, user_id=test_user.id,
            status="ready", target_column="target", dataset_path=tmp_path
        )
        db_session.add(model)
        db_session.commit()

        # 2. Создаем фейковые прогнозы, чтобы активировать анализ сегментов
        for i in range(5):
            pred = PredictionHistory(
                user_id=test_user.id, model_version_id=model.id,
                input_data={"age": 20, "gender": "M", "education": "High"},
                probability=0.8, prediction=1
            )
            db_session.add(pred)
        db_session.commit()

        # 3. Запрашиваем аналитику
        response = client.get(f"/api/models/{model.id}/analytics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Проверяем, что сегменты и выводы посчитались
        assert "segments" in data["predictions"]
        assert len(data["insights"]) > 0

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_analytics_invalid_target(client, auth_headers, db_session, test_user):
    """Тест на ошибку, если в CSV нет целевой колонки"""
    df = pd.DataFrame({"age": [20, 30]})

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    try:
        model = ModelVersion(
            version="bad_target", metrics={}, user_id=test_user.id,
            status="ready", target_column="missing_col", dataset_path=tmp_path
        )
        db_session.add(model)
        db_session.commit()

        response = client.get(f"/api/models/{model.id}/analytics", headers=auth_headers)
        assert response.status_code == 422  # Ошибка валидации
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)