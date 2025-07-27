from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.content import Content
from pgmcp.models.mixin import IsContentableMixin, IsListableMixin, IsSectionableMixin


class Paragraph(IsContentableMixin, IsSectionableMixin, IsListableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__      = "paragraphs"

    # == Columns ============================================================== 
    section_item_id: Mapped[int] = mapped_column(ForeignKey("section_items.id"), nullable=False)

    # == Relationships ========================================================
    
    sentences: Mapped[list[Content]] = relationship(
        "Sentence",
        back_populates="paragraph",
        cascade="all, delete-orphan",
        lazy="joined"
    )
    
    # == Methods ==============================================================
