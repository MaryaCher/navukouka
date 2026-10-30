from app.db.database import Base, engine
from app.db import models


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Таблицы базы данных успешно созданы.")


if __name__ == "__main__":
    init_db()