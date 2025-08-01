"""Add missing ForeignKeys to models

Revision ID: e8cbccfb1e23
Revises: 10251b001292
Create Date: 2025-07-19 20:44:06.577892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'e8cbccfb1e23'
down_revision: Union[str, None] = '10251b001292'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, 'answers', 'contents', ['content_id'], ['id'])
    op.create_foreign_key(None, 'documents', 'corpora', ['corpus_id'], ['id'])
    op.create_foreign_key(None, 'listing_items', 'listings', ['listing_id'], ['id'])
    op.create_foreign_key(None, 'listings', 'section_items', ['section_item_id'], ['id'])
    op.create_foreign_key(None, 'paragraphs', 'section_items', ['section_item_id'], ['id'])
    op.create_foreign_key(None, 'sections', 'documents', ['document_id'], ['id'])
    op.create_foreign_key(None, 'sentences', 'paragraphs', ['paragraph_id'], ['id'])
    op.create_foreign_key(None, 'table_rows', 'tables', ['table_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'table_rows', type_='foreignkey')
    op.drop_constraint(None, 'sentences', type_='foreignkey')
    op.drop_constraint(None, 'sections', type_='foreignkey')
    op.drop_constraint(None, 'paragraphs', type_='foreignkey')
    op.drop_constraint(None, 'listings', type_='foreignkey')
    op.drop_constraint(None, 'listing_items', type_='foreignkey')
    op.drop_constraint(None, 'documents', type_='foreignkey')
    op.drop_constraint(None, 'answers', type_='foreignkey')
    # ### end Alembic commands ###
