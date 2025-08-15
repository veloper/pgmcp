"""
Alembic migration for moving chunk embeddings to the new Embedding model/table.

- Creates the embeddings table with IVFFlat index.
- Migrates existing chunk.embedding data to the new table.
- Removes the embedding column from chunks.
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '20250814_migrate_chunk_embeddings'
down_revision = None  # Set to previous migration revision
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create embeddings table
    op.create_table(
        'embeddings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('chunk_id', sa.Integer(), sa.ForeignKey('chunks.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
    sa.Column('vector', Vector(1536), nullable=False),
    )
    op.create_index(
        'ix_embeddings_vector_ivfflat_cosine',
        'embeddings',
        ['vector'],
        postgresql_using='ivfflat',
        postgresql_ops={'vector': 'vector_cosine_ops'},
        postgresql_with={'lists': 100},
    )

    # 2. Migrate data from chunks.embedding to embeddings
    conn = op.get_bind()
    # Only migrate if the old column exists
    chunk_table = sa.Table('chunks', sa.MetaData(), autoload_with=conn)
    if 'embedding' in chunk_table.c:
        result = conn.execute(sa.text('SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL'))
        for row in result:
            conn.execute(sa.text('INSERT INTO embeddings (chunk_id, vector) VALUES (:chunk_id, :vector)'), {'chunk_id': row.id, 'vector': row.embedding})

    # 3. Remove embedding column from chunks
    if 'embedding' in chunk_table.c:
        op.drop_column('chunks', 'embedding')

def downgrade():
    # 1. Add embedding column back to chunks
    op.add_column('chunks', sa.Column('embedding', Vector(1536), nullable=True))
    # 2. Migrate data back from embeddings
    conn = op.get_bind()
    result = conn.execute(sa.text('SELECT chunk_id, vector FROM embeddings'))
    for row in result:
        conn.execute(sa.text('UPDATE chunks SET embedding = :vector WHERE id = :chunk_id'), {'chunk_id': row.chunk_id, 'vector': row.vector})
    # 3. Drop embeddings table
    op.drop_index('ix_embeddings_vector_ivfflat_cosine', table_name='embeddings')
    op.drop_table('embeddings')
