"""Change CrawlJob JSON columns to JSONB

Revision ID: 7a4260159cb7
Revises: c2117c48735c
Create Date: 2025-07-22 15:15:27.262478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a4260159cb7'
down_revision: Union[str, None] = 'c2117c48735c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('code_blocks', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('code_blocks', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('code_blocks', sa.Column('sectionable_id', sa.Integer(), nullable=True))
    op.add_column('code_blocks', sa.Column('sectionable_type', sa.String(), nullable=False))
    op.add_column('crawl_jobs', sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.alter_column('crawl_jobs', 'start_urls',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=False)
    op.alter_column('crawl_jobs', 'settings',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=False)
    op.alter_column('crawl_jobs', 'allowed_domains',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=False)
    op.create_foreign_key(None, 'crawl_logs', 'crawl_jobs', ['crawl_job_id'], ['id'])
    op.create_foreign_key(None, 'crawl_logs', 'crawl_items', ['crawl_item_id'], ['id'])
    op.add_column('documents', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('listing_items', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('listing_items', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('listings', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('listings', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('listings', sa.Column('sectionable_id', sa.Integer(), nullable=True))
    op.add_column('listings', sa.Column('sectionable_type', sa.String(), nullable=False))
    op.add_column('listings', sa.Column('listable_id', sa.Integer(), nullable=True))
    op.add_column('listings', sa.Column('listable_type', sa.String(), nullable=False))
    op.add_column('paragraphs', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('paragraphs', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('paragraphs', sa.Column('sectionable_id', sa.Integer(), nullable=True))
    op.add_column('paragraphs', sa.Column('sectionable_type', sa.String(), nullable=False))
    op.add_column('paragraphs', sa.Column('listable_id', sa.Integer(), nullable=True))
    op.add_column('paragraphs', sa.Column('listable_type', sa.String(), nullable=False))
    op.create_foreign_key(None, 'section_items', 'sections', ['section_id'], ['id'])
    op.add_column('sections', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('sections', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('sentences', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('sentences', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('table_row_cells', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('table_row_cells', sa.Column('contentable_type', sa.String(), nullable=False))
    op.create_foreign_key(None, 'table_row_cells', 'table_rows', ['table_row_id'], ['id'])
    op.add_column('table_rows', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('table_rows', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('tables', sa.Column('contentable_id', sa.Integer(), nullable=True))
    op.add_column('tables', sa.Column('contentable_type', sa.String(), nullable=False))
    op.add_column('tables', sa.Column('sectionable_id', sa.Integer(), nullable=True))
    op.add_column('tables', sa.Column('sectionable_type', sa.String(), nullable=False))
    op.add_column('tables', sa.Column('listable_id', sa.Integer(), nullable=True))
    op.add_column('tables', sa.Column('listable_type', sa.String(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tables', 'listable_type')
    op.drop_column('tables', 'listable_id')
    op.drop_column('tables', 'sectionable_type')
    op.drop_column('tables', 'sectionable_id')
    op.drop_column('tables', 'contentable_type')
    op.drop_column('tables', 'contentable_id')
    op.drop_column('table_rows', 'contentable_type')
    op.drop_column('table_rows', 'contentable_id')
    op.drop_constraint(None, 'table_row_cells', type_='foreignkey')
    op.drop_column('table_row_cells', 'contentable_type')
    op.drop_column('table_row_cells', 'contentable_id')
    op.drop_column('sentences', 'contentable_type')
    op.drop_column('sentences', 'contentable_id')
    op.drop_column('sections', 'contentable_type')
    op.drop_column('sections', 'contentable_id')
    op.drop_constraint(None, 'section_items', type_='foreignkey')
    op.drop_column('paragraphs', 'listable_type')
    op.drop_column('paragraphs', 'listable_id')
    op.drop_column('paragraphs', 'sectionable_type')
    op.drop_column('paragraphs', 'sectionable_id')
    op.drop_column('paragraphs', 'contentable_type')
    op.drop_column('paragraphs', 'contentable_id')
    op.drop_column('listings', 'listable_type')
    op.drop_column('listings', 'listable_id')
    op.drop_column('listings', 'sectionable_type')
    op.drop_column('listings', 'sectionable_id')
    op.drop_column('listings', 'contentable_type')
    op.drop_column('listings', 'contentable_id')
    op.drop_column('listing_items', 'contentable_type')
    op.drop_column('listing_items', 'contentable_id')
    op.drop_column('documents', 'contentable_type')
    op.drop_column('documents', 'contentable_id')
    op.drop_constraint(None, 'crawl_logs', type_='foreignkey')
    op.drop_constraint(None, 'crawl_logs', type_='foreignkey')
    op.alter_column('crawl_jobs', 'allowed_domains',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=False)
    op.alter_column('crawl_jobs', 'settings',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=False)
    op.alter_column('crawl_jobs', 'start_urls',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=False)
    op.drop_column('crawl_jobs', 'stats')
    op.drop_column('code_blocks', 'sectionable_type')
    op.drop_column('code_blocks', 'sectionable_id')
    op.drop_column('code_blocks', 'contentable_type')
    op.drop_column('code_blocks', 'contentable_id')
    # ### end Alembic commands ###
