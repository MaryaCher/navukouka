
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_model(
    y_true: Any,
    probabilities: Any,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Вычисляет метрики качества бинарной классификации."""
    y_true = np.asarray(y_true, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    predictions = (probabilities >= threshold).astype(int)

    if len(y_true) == 0:
        raise ValueError("Невозможно оценить модель на пустой выборке.")

    if len(y_true) != len(probabilities):
        raise ValueError("Число прогнозов не совпадает с числом ответов.")

    if not np.isfinite(probabilities).all():
        raise ValueError("Вероятности содержат некорректные значения.")

    if not np.isin(y_true, [0, 1]).all():
        raise ValueError("Истинные значения должны быть 0 или 1.")

    if ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Вероятности должны находиться в диапазоне от 0 до 1.")

    auc = (
        float(roc_auc_score(y_true, probabilities))
        if len(np.unique(y_true)) == 2
        else None
    )

    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])

    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": auc,
        "confusion_matrix": matrix.tolist(),
        "threshold": threshold,
    }