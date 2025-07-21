from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from pgmcp.models.base import Base
from pgmcp.models.content import Content
from pgmcp.models.mixin import IsContentableMixin, IsListableMixin, IsSectionableMixin


class CodeBlock(IsContentableMixin, IsSectionableMixin, Base):
    
    # == Model Metadata =======================================================
    __tablename__ = "code_blocks"
    
    # == Columns ============================================================== 
    section_item_id: Mapped[int] = mapped_column(nullable=False)
    language: Mapped[str | None] = mapped_column(nullable=True)
    
    # == Relationships ========================================================
    
    # == Methods ==============================================================
