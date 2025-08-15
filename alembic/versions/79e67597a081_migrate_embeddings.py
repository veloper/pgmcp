"""migrate_embeddings

Revision ID: 79e67597a081
Revises: e3688c486b85
Create Date: 2025-08-14 18:07:34.710041

"""
from typing import Sequence, Union

import sqlalchemy as sa

from pgvector.sqlalchemy import Vector

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '79e67597a081'
down_revision: Union[str, None] = 'e3688c486b85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO embeddings (vector, chunk_id)
        SELECT embedding, id FROM chunks
        WHERE embedding IS NOT NULL
    """))
    conn.execute(sa.text("""
        UPDATE chunks SET embedding = NULL WHERE embedding IS NOT NULL
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE chunks
        SET embedding = e.vector
        FROM embeddings e
        WHERE chunks.id = e.chunk_id
          AND e.vector IS NOT NULL
    """))
    conn.execute(sa.text("""
        DELETE FROM embeddings
        WHERE chunk_id IN (SELECT id FROM chunks WHERE embedding IS NOT NULL)
    """))
