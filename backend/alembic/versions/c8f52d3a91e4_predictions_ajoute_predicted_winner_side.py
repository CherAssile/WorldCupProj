"""predictions: ajoute predicted_winner_side (qualifié par côté)

Un match à placeholders (ex. la finale avant la fin des demies) devient pronostiquable :
le qualifié s'y exprime par le côté (HOME/AWAY) puisque l'équipe n'est pas encore connue.
Champ nullable, mutuellement exclusif avec predicted_winner_team_id (imposé côté
application, comme le reste des règles du qualifié).

Revision ID: c8f52d3a91e4
Revises: 4a1f86318170
Create Date: 2026-07-18 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f52d3a91e4'
down_revision: Union[str, None] = '4a1f86318170'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

predicted_winner_side = sa.Enum('HOME', 'AWAY', name='predicted_winner_side')


def upgrade() -> None:
    predicted_winner_side.create(op.get_bind(), checkfirst=True)
    op.add_column('predictions', sa.Column('predicted_winner_side', predicted_winner_side, nullable=True))


def downgrade() -> None:
    op.drop_column('predictions', 'predicted_winner_side')
    predicted_winner_side.drop(op.get_bind(), checkfirst=True)
