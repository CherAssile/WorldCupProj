from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.award_prediction import AwardPrediction
    from app.models.prediction import Prediction
    from app.models.score import Score
    from app.models.simulation_run import SimulationRun
    from app.models.training_session import TrainingSession


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="user")
    award_predictions: Mapped[list["AwardPrediction"]] = relationship(back_populates="user")
    score: Mapped[Optional["Score"]] = relationship(back_populates="user")
    training_sessions: Mapped[list["TrainingSession"]] = relationship(back_populates="user")
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(back_populates="created_by")
