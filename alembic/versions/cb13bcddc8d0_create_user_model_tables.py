"""create user model tables

Revision ID: cb13bcddc8d0
Revises: cd7da7af540d_initial
Create Date: 2025-07-11 16:48:13.647877

"""
from typing import Sequence, Union

import sqlalchemy as sa

from pgvector.sqlalchemy import Vector

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'cb13bcddc8d0'
down_revision: Union[str, None] = 'cd7da7af540d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
