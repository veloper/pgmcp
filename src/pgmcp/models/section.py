from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin


if TYPE_CHECKING:
    from pgmcp.models.document import Document
    from pgmcp.models.section_item import SectionItem


class Section(IsContentableMixin, Base):
    """
    Represents a section in a document, which can contain various types of sectionable content.
    """

    # == Model Metadata =======================================================
    __tablename__ = "sections"

    # == Columns ============================================================== 
    title       : Mapped[str | None] = mapped_column(nullable=True)
    document_id : Mapped[int | None] = mapped_column(nullable=True)

    # == Relationships ========================================================
    
    # has_many :section_items, inverse_of: :section
    section_items : Mapped[list[SectionItem]] = relationship(
        "SectionItem",
        back_populates = "section",
        cascade        = "all, delete-orphan",
        lazy           = "joined"
    )
    
    # belongs_to :document, inverse_of: :sections
    document : Mapped[Document | None] = relationship( "Document", back_populates = "sections" )

    # == Methods ==============================================================
