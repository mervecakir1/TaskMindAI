"""phone number added

Revision ID: 11653859ebf3
Revises: 
Create Date: 2026-03-17 23:54:30.880089

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11653859ebf3'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users',sa.Column('phone_number', sa.String(),nullable=True))


def downgrade() -> None:
    pass
