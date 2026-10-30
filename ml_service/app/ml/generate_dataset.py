
from pathlib import Path

import numpy as np
import pandas as pd


def generate_dataset(
    n_users: int = 1000,
    random_state: int = 42,
) -> pd.DataFrame:
    """Генерирует синтетические данные для тестирования ML-модели."""

    if n_users < 100:
        raise ValueError("Необходимо не менее 100 записей.")

    rng = np.random.default_rng(random_state)

    age = rng.integers(18, 71, size=n_users)

    gender = rng.choice(
        ["Мужской", "Женский"],
        size=n_users,
    )

    marital_status = rng.choice(
        ["Не состоит в браке", "Состоит в браке", "Разведён(а)"],
        size=n_users,
        p=[0.35, 0.50, 0.15],
    )

    children_count = rng.choice(
        [0, 1, 2, 3, 4],
        size=n_users,
        p=[0.35, 0.20, 0.28, 0.12, 0.05],
    )

    education = rng.choice(
        ["Среднее", "Среднее специальное", "Высшее", "Послевузовское"],
        size=n_users,
        p=[0.20, 0.30, 0.40, 0.10],
    )

    profession = rng.choice(
        [
            "Инженер",
            "Учитель",
            "Врач",
            "Менеджер",
            "Рабочий",
            "Предприниматель",
            "Студент",
            "Другое",
        ],
        size=n_users,
    )

    income = np.round(
        rng.lognormal(mean=np.log(70000), sigma=0.55, size=n_users)
    ).astype(int)
    income = np.clip(income, 15000, 500000)

    industry = rng.choice(
        [
            "Образование",
            "Здравоохранение",
            "Промышленность",
            "Торговля",
            "Информационные технологии",
            "Строительство",
            "Финансы",
            "Другое",
        ],
        size=n_users,
    )

    residence_type = rng.choice(
        ["Город", "Деревня"],
        size=n_users,
        p=[0.75, 0.25],
    )

    nationality = rng.choice(
        ["Русский", "Татарин", "Башкир", "Чуваш", "Другая"],
        size=n_users,
        p=[0.70, 0.10, 0.07, 0.05, 0.08],
    )

    # Условная вероятность для демонстрации работы алгоритма.
    # Коэффициенты придуманы для синтетических данных
    # и не являются выводами о реальных людях.

    score = (
            -1.2
            + 0.070 * (age - 35)
            + 0.000035 * (income - 70000)
            + 1.00 * (education == "Высшее")
            + 1.40 * (education == "Послевузовское")
            + 0.90 * (industry == "Информационные технологии")
            + 0.60 * (residence_type == "Город")
    )

    probability = 1 / (1 + np.exp(-score))
    target_action = rng.binomial(1, probability)

    return pd.DataFrame({
        "age": age,
        "gender": gender,
        "marital_status": marital_status,
        "children_count": children_count,
        "education": education,
        "profession": profession,
        "income": income,
        "industry": industry,
        "residence_type": residence_type,
        "nationality": nationality,
        "target_action": target_action,
    })


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parents[2]
    output_dir = project_dir / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = generate_dataset(n_users=5000)
    output_path = output_dir / "users_dataset.csv"

    dataset.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Датасет сохранён: {output_path}")
    print(f"Количество записей: {len(dataset)}")
    print("\nРаспределение целевого действия:")
    print(dataset["target_action"].value_counts())
    print("\nПримеры записей:")
    print(dataset.head().to_string(index=False))