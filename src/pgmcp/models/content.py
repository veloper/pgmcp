from __future__ import annotations

from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import generic_relationship

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin


class Content(Base):
    """Polymorphic model that holds a standardized content field of text type and can be used to attach content to any other model."""

    # == Metadata =========================================================
    __tablename__ = "contents"
    __mapper_args__ = {
        "polymorphic_on": "contentable_type",
        "polymorphic_identity": "contentable",
        "with_polymorphic": "*",
    }

    # == Columns ==========================================================
    id: Mapped[int] = mapped_column(primary_key=True)
    contentable_id: Mapped[int | None] = mapped_column(nullable=True)
    contentable_type: Mapped[str] = mapped_column(nullable=False)
    text: Mapped[str | None] = mapped_column(nullable=True)
    size: Mapped[int | None] = mapped_column(nullable=True)
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)

    # == Relationships ====================================================

    # == Methods ==========================================================
    
    # Equivalent To: belongs_to(:contentable), polymorphic: true
    contentable = generic_relationship(contentable_type, contentable_id)
