"""ai_predictions: ajoute is_fallback (prédiction de repli neutre)

Quand le modèle ne reconnaît pas une équipe (absente de son dataset, ex. Curaçao),
l'IA sert en compétitif une prédiction de repli neutre (nul 1-1) plutôt que de rester
muette : elle concourt au classement et ne doit pas partir avec un handicap invisible.
is_fallback marque ces prédictions pour rester honnête sur leur nature.

Revision ID: d3f6b1c48a02
Revises: e7a94b0c25d1
Create Date: 2026-07-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f6b1c48a02'
down_revision: Union[str, None] = 'e7a94b0c25d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ai_predictions',
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # server_default posé pour les lignes existantes ; retiré ensuite, la valeur est
    # désormais fournie par l'application.
    op.alter_column('ai_predictions', 'is_fallback', server_default=None)


def downgrade() -> None:
    op.drop_column('ai_predictions', 'is_fallback')
