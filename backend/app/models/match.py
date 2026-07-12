from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MatchPhase, MatchStatus

if TYPE_CHECKING:
    from app.models.ai_prediction import AiPrediction
    from app.models.prediction import Prediction
    from app.models.team import Team


class Match(Base):
    """Match du tournoi en cours (mode compétitif). Verrouillé côté serveur à kickoff_at."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable : un match de phase finale existe (date, terrain) avant que ses deux
    # participants ne soient connus (ex. la finale, tant que les demies ne sont pas jouées).
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    # Référence l'équipe non encore résolue (ex. "W101" = vainqueur du match 101),
    # le temps que home_team_id/away_team_id puissent être renseignés.
    home_placeholder: Mapped[str | None] = mapped_column(String(50), nullable=True)
    away_placeholder: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Numéro de match côté source : sert à résoudre les placeholders et à dédoublonner
    # les matchs de phase finale de façon stable, indépendamment des équipes.
    num: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    phase: Mapped[MatchPhase] = mapped_column(SqlEnum(MatchPhase, name="match_phase"), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        SqlEnum(MatchStatus, name="match_status"), default=MatchStatus.SCHEDULED, nullable=False
    )
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Score du temps réglementaire (90 min + arrêts) : seul celui-ci sert au scoring des
    # pronostics (règle du projet), quelle que soit l'issue finale du match.
    home_score: Mapped[int | None] = mapped_column(nullable=True)
    away_score: Mapped[int | None] = mapped_column(nullable=True)
    # Décision finale d'un match à élimination directe, si le temps réglementaire ne suffit
    # pas. Ne servent jamais au scoring des pronostics, seulement à déterminer le vainqueur.
    extra_time_home_score: Mapped[int | None] = mapped_column(nullable=True)
    extra_time_away_score: Mapped[int | None] = mapped_column(nullable=True)
    penalties_home_score: Mapped[int | None] = mapped_column(nullable=True)
    penalties_away_score: Mapped[int | None] = mapped_column(nullable=True)
    # Équipe qualifiée tous prolongements confondus (tirs au but > prolongation > temps
    # réglementaire). NULL pour un match de groupe nul, ou tant que le match n'est pas joué.
    winner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    home_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[away_team_id], back_populates="away_matches")
    winner_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[winner_team_id], back_populates="won_matches")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="match")
    ai_prediction: Mapped[Optional["AiPrediction"]] = relationship(back_populates="match")
