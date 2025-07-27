"""add analyzer fields

Revision ID: 6a8fbe76a84d
Revises: d735a46bdc3d
Create Date: 2025-07-20 18:25:06.932875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a8fbe76a84d'
down_revision: Union[str, Sequence[str], None] = 'd735a46bdc3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('rave_articles',
                  sa.Column('relevance_score', sa.Float(), nullable=True))
    op.add_column('rave_articles',
                  sa.Column('developer_focus', sa.Boolean(), nullable=False, server_default=sa.text('false')))



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('rave_articles', 'relevance_score')
    op.drop_column('rave_articles', 'developer_focus')