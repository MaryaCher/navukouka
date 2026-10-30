
import json
from pathlib import Path
from typing import Any

from catboost import CatBoostClassifier


class ModelStorage:
    def __init__(self, models_dir: Path | str = "models") -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Пути для совместимости с существующей моделью.
        self.model_path = self.models_dir / "catboost_model.cbm"
        self.metadata_path = self.models_dir / "model_metadata.json"

    def save(
        self,
        model: CatBoostClassifier,
        metadata: dict[str, Any],
        model_id: str | None = None,
    ) -> None:
        if model_id is None:
            model_path = self.model_path
            metadata_path = self.metadata_path
        else:
            model_dir = self._get_model_dir(model_id)
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / "model.cbm"
            metadata_path = model_dir / "metadata.json"

        model.save_model(str(model_path))

        with metadata_path.open("w", encoding="utf-8") as file:
            json.dump(
                metadata,
                file,
                ensure_ascii=False,
                indent=2,
            )

    def load(
        self,
        model_id: str | None = None,
    ) -> tuple[CatBoostClassifier, dict[str, Any]]:
        if model_id is not None:
            model_dir = self._get_model_dir(model_id)
            model_path = model_dir / "model.cbm"
            metadata_path = model_dir / "metadata.json"
        else:
            # Сначала используем старую модель, если она существует.
            if self.model_path.exists() and self.metadata_path.exists():
                model_path = self.model_path
                metadata_path = self.metadata_path

            else:
                candidates = [
                    path
                    for path in self.models_dir.iterdir()
                    if path.is_dir()
                       and (path / "model.cbm").is_file()
                       and (path / "metadata.json").is_file()
                ]

                if self.model_path.is_file() and self.metadata_path.is_file():
                    candidates.append(self.models_dir)

                if not candidates:
                    raise FileNotFoundError(
                        "Сохранённые модели не найдены."
                    )

                def get_metadata_path(path: Path) -> Path:
                    if path == self.models_dir:
                        return self.metadata_path
                    return path / "metadata.json"

                latest_dir = max(
                    candidates,
                    key=lambda path: get_metadata_path(path).stat().st_mtime,
                )

                if latest_dir == self.models_dir:
                    model_path = self.model_path
                    metadata_path = self.metadata_path
                else:
                    model_path = latest_dir / "model.cbm"
                    metadata_path = latest_dir / "metadata.json"

        if not model_path.is_file():
            raise FileNotFoundError(
                f"Файл модели не найден: {model_path}"
            )

        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"Метаданные модели не найдены: {metadata_path}"
            )

        model = CatBoostClassifier()
        model.load_model(str(model_path))

        with metadata_path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)

        return model, metadata

    def _get_model_dir(self, model_id: str) -> Path:
        """Возвращает каталог модели, не допуская выхода за models_dir."""
        if (
            not model_id
            or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in model_id)
        ):
            raise ValueError("Некорректный идентификатор модели.")

        return self.models_dir / model_id