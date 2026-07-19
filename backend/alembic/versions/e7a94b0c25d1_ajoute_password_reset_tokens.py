"""ajoute password_reset_tokens (réinitialisation de mot de passe)

Jetons à usage unique, valables 1 heure. Seul le hash SHA-256 du jeton est stocké
(token_hash, unique) : le jeton en clair ne circule que dans le lien e-mail. used_at
marque la consommation, expires_at la limite de validité.

Revision ID: e7a94b0c25d1
Revises: c8f52d3a91e4
Create Date: 2026-07-18 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a94b0c25d1'
down_revision: Union[str, None] = 'c8f52d3a91e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
