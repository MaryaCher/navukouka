
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Role(Base):

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    """Учётная запись пользователя."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    role: Mapped["Role"] = relationship(back_populates="users")
    predictions: Mapped[list["PredictionHistory"]] = relationship(
        back_populates="user"
    )
    models: Mapped[list["ModelVersion"]] = relationship(back_populates="owner")
    prediction_batches: Mapped[list["PredictionBatch"]] = relationship(
        back_populates="user"
    )


class ModelVersion(Base):
    """Информация об обученной версии модели."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_column: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ready", server_default="ready"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    dataset_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    owner: Mapped["User | None"] = relationship(back_populates="models")
    predictions: Mapped[list["PredictionHistory"]] = relationship(
        back_populates="model_version"
    )
    prediction_batches: Mapped[list["PredictionBatch"]] = relationship(
        back_populates="model_version"
    )


class PredictionBatch(Base):
    """Один запуск пакетного прогнозирования."""

    __tablename__ = "prediction_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id"), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="processing", server_default="processing"
    )
    total_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    successful_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    failed_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="prediction_batches")
    model_version: Mapped["ModelVersion | None"] = relationship(
        back_populates="prediction_batches"
    )
    predictions: Mapped[list["PredictionHistory"]] = relationship(
        back_populates="batch"
    )


class PredictionHistory(Base):
    """История одиночных и пакетных прогнозов."""

    __tablename__ = "prediction_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id"), nullable=True, index=True
    )
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("prediction_batches.id"), nullable=True, index=True
    )

    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    prediction: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="predictions")
    model_version: Mapped["ModelVersion | None"] = relationship(
        back_populates="predictions"
    )
    batch: Mapped["PredictionBatch | None"] = relationship(
        back_populates="predictions"
    )