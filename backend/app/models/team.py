from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.historical_match import HistoricalMatch
    from app.models.match import Match
    from app.models.player import Player
    from app.models.simulation_match_result import SimulationMatchResult


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    fifa_code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    flag_url: Mapped[str | None] = mapped_column(String(255))
    group_name: Mapped[str | None] = mapped_column(String(20), nullable=True)

    players: Mapped[list["Player"]] = relationship(back_populates="team")
    home_matches: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches: Mapped[list["Match"]] = relationship(
        foreign_keys="Match.away_team_id", back_populates="away_team"
    )
    home_historical_matches: Mapped[list["HistoricalMatch"]] = relationship(
        foreign_keys="HistoricalMatch.home_team_id", back_populates="home_team"
    )
    away_historical_matches: Mapped[list["HistoricalMatch"]] = relationship(
        foreign_keys="HistoricalMatch.away_team_id", back_populates="away_team"
    )
    home_simulation_match_results: Mapped[list["SimulationMatchResult"]] = relationship(
        foreign_keys="SimulationMatchResult.home_team_id", back_populates="home_team"
    )
    away_simulation_match_results: Mapped[list["SimulationMatchResult"]] = relationship(
        foreign_keys="SimulationMatchResult.away_team_id", back_populates="away_team"
    )
