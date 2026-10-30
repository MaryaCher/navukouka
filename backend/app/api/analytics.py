from pathlib import Path
from typing import Any
from itertools import combinations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User, ModelVersion, PredictionHistory


router = APIRouter()


# ============================================================
# HELPERS
# ============================================================


def detect_feature_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    numeric = pd.to_numeric(series, errors="coerce")
    non_null_count = series.notna().sum()

    if non_null_count == 0:
        return "categorical"

    numeric_ratio = numeric.notna().sum() / non_null_count
    return "numeric" if numeric_ratio >= 0.9 else "categorical"


def make_json_safe(value: Any) -> Any:
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def detect_positive_class(series: pd.Series) -> str:
    values = (
        series.dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if not values:
        return "1"

    if "1" in values:
        return "1"

    if len(values) >= 2:
        return sorted(values)[-1]

    return values[0]


# ============================================================
# FEATURE ANALYSIS
# ============================================================


def analyze_categorical_feature(
    dataframe: pd.DataFrame,
    feature: str,
    target_column: str,
    positive_class: str,
) -> dict[str, Any]:

    work = dataframe[[feature, target_column]].copy()
    work[feature] = work[feature].fillna("(пропуск)").astype(str)

    result = []

    for value, group in work.groupby(feature, dropna=False):
        count = len(group)

        positive_count = int(
            (group[target_column].astype(str) == positive_class).sum()
        )

        conversion = (
            round(positive_count / count * 100, 2)
            if count
            else None
        )

        result.append(
            {
                "value": value,
                "count": count,
                "positive_count": positive_count,
                "conversion": conversion,
            }
        )

    result.sort(key=lambda item: item["count"], reverse=True)

    return {"type": "categorical", "categories": result}


def analyze_numeric_feature(
    dataframe: pd.DataFrame,
    feature: str,
    target_column: str,
    positive_class: str,
) -> dict[str, Any]:

    work = dataframe[[feature, target_column]].copy()
    work[feature] = pd.to_numeric(work[feature], errors="coerce")
    work = work.dropna(subset=[feature])

    if work.empty:
        return {"type": "numeric", "distribution": None, "bins": []}

    values = work[feature]

    distribution = {
        "min": make_json_safe(values.min()),
        "max": make_json_safe(values.max()),
        "mean": round(float(values.mean()), 4),
        "median": round(float(values.median()), 4),
        "std": (
            round(float(values.std()), 4)
            if len(values) > 1
            else 0
        ),
    }

    unique_count = values.nunique()

    if unique_count <= 1:
        return {
            "type": "numeric",
            "distribution": distribution,
            "bins": [],
        }

    try:
        bins = pd.qcut(
            values,
            q=min(6, unique_count),
            duplicates="drop",
        )
    except ValueError:
        bins = pd.cut(values, bins=5, duplicates="drop")

    grouped = work.groupby(bins, observed=True)

    result = []

    for interval, group in grouped:
        count = len(group)

        positive_count = int(
            (group[target_column].astype(str) == positive_class).sum()
        )

        conversion = (
            round(positive_count / count * 100, 2)
            if count
            else None
        )

        result.append(
            {
                "from": make_json_safe(interval.left),
                "to": make_json_safe(interval.right),
                "count": count,
                "positive_count": positive_count,
                "conversion": conversion,
            }
        )

    return {
        "type": "numeric",
        "distribution": distribution,
        "bins": result,
    }


# ============================================================
# PREDICTIONS
# ============================================================


def analyze_predictions(
    predictions: list[PredictionHistory],
) -> dict[str, Any]:

    if not predictions:
        return {
            "total": 0,
            "average_probability": None,
            "prediction_distribution": {},
            "probability_distribution": [],
            "segments": [],
            "calibration": [],
        }

    probabilities = [float(item.probability) for item in predictions]

    prediction_distribution: dict[str, int] = {}

    for item in predictions:
        key = str(item.prediction)
        prediction_distribution[key] = prediction_distribution.get(key, 0) + 1

    if probabilities and max(probabilities) > 1:
        normalized = [value / 100 for value in probabilities]
    else:
        normalized = probabilities

    average_probability = (
        sum(normalized) / len(normalized) if normalized else None
    )

    probability_bins = [
        (0.0, 0.1),
        (0.1, 0.2),
        (0.2, 0.3),
        (0.3, 0.4),
        (0.4, 0.5),
        (0.5, 0.6),
        (0.6, 0.7),
        (0.7, 0.8),
        (0.8, 0.9),
        (0.9, 1.0),
    ]

    distribution = []

    for left, right in probability_bins:
        if right == 1.0:
            selected = [v for v in normalized if left <= v <= right]
        else:
            selected = [v for v in normalized if left <= v < right]

        distribution.append(
            {"from": left, "to": right, "count": len(selected)}
        )

    return {
        "total": len(predictions),
        "average_probability": (
            round(average_probability, 4)
            if average_probability is not None
            else None
        ),
        "prediction_distribution": prediction_distribution,
        "probability_distribution": distribution,
        "segments": [],
        "calibration": [],
    }


# ============================================================
# SEGMENTS
# ============================================================


def build_segments(
    predictions: list[PredictionHistory],
    columns_info: list[dict[str, Any]],
    min_size: int = 5,
    top_n: int = 5,
) -> list[dict[str, Any]]:

    if len(predictions) < min_size:
        return []

    rows = []

    for item in predictions:
        if not isinstance(item.input_data, dict):
            continue

        row = dict(item.input_data)

        probability = float(item.probability)
        if probability > 1:
            probability = probability / 100

        row["_prob"] = probability
        rows.append(row)

    if not rows:
        return []

    dataframe = pd.DataFrame(rows)

    categorical = [
        column["name"]
        for column in columns_info
        if column["type"] == "categorical"
        and 1 < column["unique"] <= 12
        and column["name"] in dataframe.columns
    ]

    if len(categorical) < 2:
        return []

    segments = []

    for pair in combinations(categorical, 2):
        work = dataframe[list(pair) + ["_prob"]].copy()

        for column in pair:
            work[column] = (
                work[column].fillna("(пропуск)").astype(str)
            )

        grouped = (
            work.groupby(list(pair), dropna=False)
            .agg(
                size=("_prob", "count"),
                average_probability=("_prob", "mean"),
            )
            .reset_index()
        )

        grouped = grouped[grouped["size"] >= min_size]

        for _, row in grouped.iterrows():
            label = " · ".join(
                f"{column}={row[column]}" for column in pair
            )

            segments.append(
                {
                    "label": label,
                    "size": int(row["size"]),
                    "average_probability": round(
                        float(row["average_probability"]), 4
                    ),
                }
            )

    segments.sort(
        key=lambda item: item["average_probability"],
        reverse=True,
    )

    return segments[:top_n]


# ============================================================
# CALIBRATION
# ============================================================


def build_calibration(
    predictions: list[PredictionHistory],
    min_count: int = 30,
) -> list[dict[str, Any]]:
    """
    Считает фактическую конверсию по децилям прогноза.

    Работает только если у прогнозов сохранена фактическая метка
    в поле actual_target. Если поле отсутствует или пустое —
    возвращает пустой список, и фронт скрывает блок.
    """

    rows = []

    for item in predictions:
        actual_target = getattr(item, "actual_target", None)

        if actual_target is None:
            continue

        probability = float(item.probability)
        if probability > 1:
            probability = probability / 100

        rows.append(
            {
                "probability": probability,
                "target": int(actual_target),
            }
        )

    if len(rows) < min_count:
        return []

    dataframe = pd.DataFrame(rows)

    try:
        dataframe["decile"] = pd.qcut(
            dataframe["probability"],
            q=10,
            labels=False,
            duplicates="drop",
        )
    except ValueError:
        return []

    grouped = (
        dataframe.groupby("decile")
        .agg(
            conversion=("target", "mean"),
            count=("target", "count"),
        )
        .reset_index()
    )

    result = []

    for _, row in grouped.iterrows():
        decile = int(row["decile"])

        result.append(
            {
                "label": f"Группа {decile + 1}",
                "conversion": round(float(row["conversion"]), 4),
                "count": int(row["count"]),
            }
        )

    return result


# ============================================================
# INSIGHTS
# ============================================================


def build_insights(
    dataframe: pd.DataFrame,
    target_series: pd.Series,
    target_column: str,
    positive_class: str,
    feature_columns: list[str],
    features_analysis: dict[str, Any],
    prediction_analysis: dict[str, Any],
) -> list[str]:

    insights: list[str] = []

    total_rows = len(dataframe)
    total_positive = int(
        (target_series.astype(str) == positive_class).sum()
    )
    base_conversion = (
        total_positive / total_rows * 100 if total_rows else 0
    )

    # 1. Базовая конверсия.
    insights.append(
        f"Целевое действие совершили {total_positive} "
        f"из {total_rows} пользователей "
        f"({base_conversion:.1f}%). Это базовый уровень конверсии."
    )

    # 2. Лучший сегмент.
    best_category = None

    for feature_name, analysis in features_analysis.items():
        if analysis["type"] != "categorical":
            continue

        for category in analysis["categories"]:
            if category["conversion"] is None:
                continue

            if category["count"] < max(20, total_rows * 0.01):
                continue

            if (
                best_category is None
                or category["conversion"] > best_category["conversion"]
            ):
                best_category = {
                    "feature": feature_name,
                    **category,
                }

    if best_category:
        diff = best_category["conversion"] - base_conversion

        if diff > 5:
            insights.append(
                f"Наибольшая конверсия — у группы "
                f"«{best_category['value']}» "
                f"по признаку «{best_category['feature']}»: "
                f"{best_category['conversion']:.1f}% "
                f"против {base_conversion:.1f}% в среднем. "
                f"Размер группы — {best_category['count']} человек. "
                f"Имеет смысл направить усилия именно на неё."
            )
        else:
            insights.append(
                f"Максимальная конверсия среди категорий — "
                f"у признака «{best_category['feature']}» "
                f"для значения «{best_category['value']}»: "
                f"{best_category['conversion']:.1f}%. "
                f"Разрыв со средним небольшой."
            )

    # 3. Худший сегмент.
    worst_category = None

    for feature_name, analysis in features_analysis.items():
        if analysis["type"] != "categorical":
            continue

        for category in analysis["categories"]:
            if category["conversion"] is None:
                continue

            if category["count"] < max(20, total_rows * 0.01):
                continue

            if (
                worst_category is None
                or category["conversion"] < worst_category["conversion"]
            ):
                worst_category = {
                    "feature": feature_name,
                    **category,
                }

    if (
        worst_category
        and base_conversion - worst_category["conversion"] > 10
    ):
        insights.append(
            f"Наименьшая конверсия — у группы "
            f"«{worst_category['value']}» "
            f"по признаку «{worst_category['feature']}»: "
            f"{worst_category['conversion']:.1f}%. "
            f"Воздействие на эту группу, вероятно, нецелесообразно."
        )

    # 4. Прогнозы.
    if prediction_analysis["total"] > 0:
        distribution = prediction_analysis["probability_distribution"]
        total_pred = sum(item["count"] for item in distribution)

        top_count = sum(
            item["count"]
            for item in distribution
            if item["from"] >= 0.8
        )

        if total_pred and top_count / total_pred >= 0.05:
            share = top_count / total_pred * 100
            insights.append(
                f"Топ-20% пользователей по прогнозной вероятности "
                f"составляют {share:.1f}% всех прогнозов. "
                f"Именно на них стоит направить основные усилия — "
                f"вероятность целевого действия у них максимальна."
            )

        avg_prob = prediction_analysis["average_probability"]

        if avg_prob is not None:
            insights.append(
                f"Средняя прогнозная вероятность по "
                f"{prediction_analysis['total']} сохранённым прогнозам — "
                f"{avg_prob * 100:.1f}%."
            )
    else:
        insights.append(
            "Для этой модели пока нет сохранённых прогнозов. "
            "Выполните прогнозирование, чтобы получить "
            "рекомендации по сегментам."
        )

    # 5. Калибровка.
    calibration = prediction_analysis.get("calibration") or []

    if len(calibration) >= 5:
        first = calibration[0]["conversion"]
        last = calibration[-1]["conversion"]

        if last > first * 1.5:
            insights.append(
                f"Модель работает корректно: в нижней группе прогноза "
                f"конверсия — {first * 100:.1f}%, "
                f"в верхней — {last * 100:.1f}%. "
                f"Прогнозам можно доверять при приоритизации."
            )
        else:
            insights.append(
                "Конверсия слабо растёт от нижней группы прогноза "
                "к верхней. Модель различает пользователей "
                "недостаточно уверенно — рекомендуется переобучение."
            )

    return insights


# ============================================================
# ENDPOINT
# ============================================================


@router.get("/models/{model_db_id}/analytics")
def get_model_analytics(
    model_db_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    model = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.id == model_db_id,
            ModelVersion.user_id == current_user.id,
        )
        .first()
    )

    if model is None:
        raise HTTPException(
            status_code=404,
            detail="Модель не найдена.",
        )

    if not model.dataset_path:
        raise HTTPException(
            status_code=404,
            detail="Для этой модели не сохранён обучающий датасет.",
        )

    dataset_path = Path(model.dataset_path)

    if not dataset_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Файл обучающего датасета модели не найден на сервере.",
        )

    try:
        dataframe = pd.read_csv(dataset_path, encoding="utf-8-sig")
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Не удалось прочитать обучающий датасет.",
        ) from error

    if dataframe.empty:
        raise HTTPException(
            status_code=422,
            detail="Обучающий датасет пуст.",
        )

    target_column = model.target_column

    if not target_column:
        raise HTTPException(
            status_code=422,
            detail="У модели не указана целевая переменная.",
        )

    if target_column not in dataframe.columns:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Целевая колонка '{target_column}' "
                "отсутствует в датасете."
            ),
        )

    # Target
    target_series = dataframe[target_column]
    positive_class = detect_positive_class(target_series)

    target_counts = (
        target_series
        .fillna("(пропуск)")
        .astype(str)
        .value_counts()
    )

    target_distribution = [
        {"value": str(value), "count": int(count)}
        for value, count in target_counts.items()
    ]

    # Columns info
    feature_columns = [
        column
        for column in dataframe.columns
        if column != target_column
    ]

    columns_info = []

    for column in feature_columns:
        series = dataframe[column]
        feature_type = detect_feature_type(series)

        columns_info.append(
            {
                "name": column,
                "type": feature_type,
                "unique": int(series.nunique(dropna=True)),
                "missing": int(series.isna().sum()),
                "missing_percent": round(
                    series.isna().mean() * 100, 2
                ),
            }
        )

    # Features analysis
    features_analysis = {}

    for column in feature_columns:
        feature_type = detect_feature_type(dataframe[column])

        if feature_type == "numeric":
            features_analysis[column] = analyze_numeric_feature(
                dataframe=dataframe,
                feature=column,
                target_column=target_column,
                positive_class=positive_class,
            )
        else:
            features_analysis[column] = analyze_categorical_feature(
                dataframe=dataframe,
                feature=column,
                target_column=target_column,
                positive_class=positive_class,
            )

    # Predictions
    predictions = (
        db.query(PredictionHistory)
        .filter(
            PredictionHistory.user_id == current_user.id,
            PredictionHistory.model_version_id == model_db_id,
        )
        .order_by(PredictionHistory.created_at.asc())
        .all()
    )

    prediction_analysis = analyze_predictions(predictions)

    prediction_analysis["segments"] = build_segments(
        predictions=predictions,
        columns_info=columns_info,
    )

    prediction_analysis["calibration"] = build_calibration(
        predictions=predictions,
    )

    # Insights
    insights = build_insights(
        dataframe=dataframe,
        target_series=target_series,
        target_column=target_column,
        positive_class=positive_class,
        feature_columns=feature_columns,
        features_analysis=features_analysis,
        prediction_analysis=prediction_analysis,
    )

    return {
        "model": {
            "id": model.id,
            "version": model.version,
            "target_column": target_column,
            "status": model.status,
            "metrics": model.metrics,
            "created_at": model.created_at.isoformat(),
        },
        "dataset": {
            "rows": len(dataframe),
            "features": len(feature_columns),
            "target": target_column,
            "positive_class": positive_class,
            "target_distribution": target_distribution,
            "columns": columns_info,
        },
        "features": features_analysis,
        "predictions": prediction_analysis,
        "insights": insights,
    }