
from pathlib import Path

import pandas as pd

from app.ml.trainer import ModelTrainer


def test_train_on_generated_dataset():
    project_dir = Path(__file__).resolve().parents[1]
    dataset_path = project_dir / "data" / "users_dataset.csv"

    assert dataset_path.exists(), "Файл датасета не найден."

    dataframe = pd.read_csv(dataset_path, encoding="utf-8-sig")

    expected_columns = {
        "age",
        "gender",
        "marital_status",
        "children_count",
        "education",
        "profession",
        "income",
        "industry",
        "residence_type",
        "nationality",
        "target_action",
    }

    assert expected_columns.issubset(dataframe.columns)
    assert len(dataframe) >= 100

    trainer = ModelTrainer(random_state=42, test_size=0.2)
    result = trainer.train(dataframe, "target_action")

    assert result["model"] is not None
    assert 0 <= result["metrics"]["accuracy"] <= 1
    assert result["metrics"]["roc_auc"] is not None
    assert len(result["features"]) == 10