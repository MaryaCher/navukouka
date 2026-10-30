from pathlib import Path
from app.core.config import settings
import pandas as pd
from app.storage.model_storage import ModelStorage
from app.ml.trainer import ModelTrainer


project_dir = Path(__file__).resolve().parent
dataset_path = project_dir / "data" / "users_dataset.csv"

dataframe = pd.read_csv(dataset_path, encoding="utf-8-sig")

trainer = ModelTrainer(random_state=42, test_size=0.2)
result = trainer.train(dataframe, "target_action")

print("\nМЕТРИКИ КАЧЕСТВА МОДЕЛИ")
for metric, value in result["metrics"].items():
    print(f"{metric}: {value}")

print("\nВАЖНОСТЬ ПРИЗНАКОВ")
for feature, importance in sorted(
    result["feature_importance"].items(),
    key=lambda item: item[1],
    reverse=True,
):
    print(f"{feature}: {importance:.4f}")

storage = ModelStorage(settings.models_dir)

storage.save(
    result["model"],
    {
        "features": result["features"],
        "class_mapping": result["class_mapping"],
        "positive_class": result["positive_class"],
        "categorical_features": result["categorical_features"],
        "metrics": result["metrics"],
        "feature_importance": result["feature_importance"],
        "target_column": "target_action",
    },
)

print(f"\nМодель сохранена: {storage.model_path}")
print(f"Метаданные сохранены: {storage.metadata_path}")