from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin, IsListableMixin, IsSectionableMixin


class Paragraph(IsContentableMixin, IsSectionableMixin, IsListableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__      = "paragraphs"

    # == Columns ============================================================== 
    section_item_id: Mapped[int] = mapped_column(nullable=False)

    # == Relationships ========================================================
    
    # == Methods ==============================================================
