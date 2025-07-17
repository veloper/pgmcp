from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base


if TYPE_CHECKING:
    from pgmcp.models.corpus import Corpus


class Library(Base):
    # == Model Metadata =======================================================
    __tablename__   = "libraries"

    # == Columns ============================================================== 
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # == Relationships ========================================================
    corpora         : Mapped[list[Corpus]] = relationship(back_populates="library")

    # == Methods ==============================================================


