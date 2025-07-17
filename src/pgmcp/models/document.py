from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from unstructured.documents.elements import Element
from unstructured.partition.html import partition_html

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin


if TYPE_CHECKING:
    from pgmcp.models.corpus import Corpus
    from pgmcp.models.section import Section


class Document(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__ = "documents"

    # == Columns ============================================================== 
    title: Mapped[str | None] = mapped_column(nullable=True)
    corpus_id: Mapped[int] = mapped_column(nullable=False)
    
    # == Relationships ========================================================
    corpus: Mapped[Corpus] = relationship("Corpus", back_populates="documents")
    
    sections: Mapped[list[Section]] = relationship(
        "Section", back_populates="document", cascade="all, delete-orphan", lazy="joined"
    )

    # == Methods ==============================================================
