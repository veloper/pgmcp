"""rename_crawl_log_table_to_plural

Revision ID: c2117c48735c
Revises: e8cbccfb1e23
Create Date: 2025-07-20 15:37:52.408313

"""
from typing import Sequence, Union

import sqlalchemy as sa

from pgvector.sqlalchemy import Vector

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c2117c48735c'
down_revision: Union[str, None] = 'e8cbccfb1e23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename table from singular to plural to follow Rails conventions
    op.rename_table('crawl_log', 'crawl_logs')


def downgrade() -> None:
    # Rename table back from plural to singular
    op.rename_table('crawl_logs', 'crawl_log')
