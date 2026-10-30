from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.storage.model_storage import ModelStorage


def test_saved_model_can_be_loaded_and_used():
    storage = ModelStorage(settings.models_dir)

    model, metadata = storage.load()

    assert model is not None
    assert "features" in metadata
    assert "target_column" in metadata

    user = pd.DataFrame([{
        "age": 35,
        "gender": "Женский",
        "marital_status": "Не состоит в браке",
        "children_count": 0,
        "education": "Высшее",
        "profession": "Инженер",
        "income": 80000,
        "industry": "Информационные технологии",
        "residence_type": "Город",
        "nationality": "Русский",
    }])

    user = user[metadata["features"]]

    probabilities = model.predict_proba(user)

    assert probabilities.shape == (1, 2)
    assert 0 <= probabilities[0][1] <= 1