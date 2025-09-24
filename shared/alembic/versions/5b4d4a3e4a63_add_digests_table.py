"""Add digests table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5b4d4a3e4a63"
down_revision: Union[str, Sequence[str], None] = "31cdded52da9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create digests table if it does not already exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "digests" in inspector.get_table_names():
        return

    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(op.f("ix_digests_url"), "digests", ["url"], unique=True)
    op.create_index(op.f("ix_digests_source"), "digests", ["source"], unique=False)


def downgrade() -> None:
    """Drop digests table if it exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "digests" not in inspector.get_table_names():
        return

    op.drop_index(op.f("ix_digests_source"), table_name="digests")
    op.drop_index(op.f("ix_digests_url"), table_name="digests")
    op.drop_table("digests")
