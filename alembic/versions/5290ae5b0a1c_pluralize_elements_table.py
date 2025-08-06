from pgvector.sqlalchemy import Vector
"""pluralize elements table

Revision ID: 5290ae5b0a1c
Revises: 4402131ef033
Create Date: 2025-08-02 14:11:46.763463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5290ae5b0a1c'
down_revision: Union[str, None] = '4402131ef033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert autogen create/drop to rename-based migration to preserve data and avoid constraint name conflicts
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Rename table element -> elements
    op.rename_table('element', 'elements')

    # 2) Rename index ix_element_type -> ix_elements_type
    op.execute('ALTER INDEX IF EXISTS ix_element_type RENAME TO ix_elements_type')

    # 3) Rename unique constraint to pluralized name to avoid duplication on create
    # Postgres supports renaming constraints directly
    # Only attempt if the old name exists
    existing_uqs = [c['name'] for c in insp.get_unique_constraints('elements')]
    if 'uq_element_type_document_id' in existing_uqs:
        op.execute('ALTER TABLE elements RENAME CONSTRAINT uq_element_type_document_id TO uq_elements_type_document_id')

    # 4) Fix self-referencing FK parent_id -> elements.id
    # Discover and drop any existing parent_id FK, then recreate with stable name
    fks = sa.inspect(bind).get_foreign_keys('elements')
    for fk in fks:
        if fk.get('constrained_columns') == ['parent_id']:
            try:
                op.drop_constraint(fk['name'], 'elements', type_='foreignkey')
            except Exception:
                pass
    # Recreate the FK with a deterministic name to avoid duplicate unnamed constraints
    op.create_foreign_key('elements_parent_id_fkey', 'elements', 'elements', ['parent_id'], ['id'])

    # 5) Ensure embedding column type is pgvector Vector(1536)
    cols = {c['name']: c for c in insp.get_columns('elements')}
    if 'embedding' not in cols:
        op.add_column('elements', sa.Column('embedding', Vector(dim=1536), nullable=True))
    else:
        try:
            op.alter_column('elements', 'embedding', type_=Vector(dim=1536), existing_nullable=True)
        except Exception:
            # If it's already Vector or incompatible cast is needed, ignore to keep migration idempotent
            pass


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop recreated parent FK (name we gave above)
    try:
        op.drop_constraint('elements_parent_id_fkey', 'elements', type_='foreignkey')
    except Exception:
        pass

    # Rename unique constraint back if present
    uqs = [c['name'] for c in insp.get_unique_constraints('elements')]
    if 'uq_elements_type_document_id' in uqs:
        op.execute('ALTER TABLE elements RENAME CONSTRAINT uq_elements_type_document_id TO uq_element_type_document_id')

    # Rename index back
    op.execute('ALTER INDEX IF EXISTS ix_elements_type RENAME TO ix_element_type')

    # Rename table back
    op.rename_table('elements', 'element')
