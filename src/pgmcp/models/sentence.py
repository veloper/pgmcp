from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from pgmcp.models.content import Content
from pgmcp.models.mixin import IsContentableMixin  # Import for relationship resolution

from .base import Base


class Sentence(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__   = "sentences"

    # == Columns ============================================================== 
    paragraph_id    : Mapped[int] = mapped_column(ForeignKey("paragraphs.id"), nullable=False)

    # == Relationships ========================================================

    # == Methods ==============================================================
