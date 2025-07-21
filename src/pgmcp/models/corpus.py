from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp import utils
from pgmcp.models.base import Base
from pgmcp.models.section import Section


if TYPE_CHECKING:
    from pgmcp.models.document import Document
    from pgmcp.models.library import Library


class Corpus(Base):
    # == Model Metadata =======================================================
    __tablename__ = "corpora"

    # == Columns ==============================================================
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    library_id: Mapped[int] = mapped_column(ForeignKey("libraries.id"), nullable=False)

    # == Relationships ========================================================
    library: Mapped[Library] = relationship(back_populates="corpora")
    
    documents: Mapped[list[Document]] = relationship("Document", back_populates="corpus")

    # == Methods ==============================================================
