"""convert_log_level_from_string_to_enum

Revision ID: 83a900f9a687
Revises: ecabc0b5bdb0
Create Date: 2025-07-22 22:01:06.722699

"""
from typing import Sequence, Union

import sqlalchemy as sa

from pgvector.sqlalchemy import Vector

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '83a900f9a687'
down_revision: Union[str, None] = 'ecabc0b5bdb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the enum type in Postgres
    op.execute(
        "CREATE TYPE log_level AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')"
    )
    # 2. Alter the column to use the new enum type
    op.alter_column(
        'crawl_logs', 'level',
        existing_type=sa.VARCHAR(),
        type_=sa.Enum('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', name='log_level'),
        existing_nullable=False,
        postgresql_using="level::log_level"
    )


def downgrade() -> None:
    # 1. Change column back to VARCHAR
    op.alter_column(
        'crawl_logs', 'level',
        existing_type=sa.Enum('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', name='log_level'),
        type_=sa.VARCHAR(),
        existing_nullable=False,
        postgresql_using="level::text"
    )
    # 2. Drop the enum type
    op.execute("DROP TYPE log_level")
