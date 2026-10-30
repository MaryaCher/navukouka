from sqlalchemy import create_engine, text

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT VERSION()"))
        version = result.scalar_one()

    print("Подключение к MySQL успешно!")
    print(f"Версия MySQL: {version}")

except Exception as error:
    print("Не удалось подключиться к MySQL.")
    print(f"Ошибка: {error}")

finally:
    engine.dispose()