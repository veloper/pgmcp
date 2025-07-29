from __future__ import annotations

from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin, IsEmbeddableMixin


if TYPE_CHECKING:
    from pgmcp.models.question import Question

class Answer(IsEmbeddableMixin, IsContentableMixin, Base):
    """Represents an answer, derived from a piece of content, that serves as a response to a specific question."""
    # == Model Metadata =======================================================
    __tablename__ = "answers"
    
    # == Columns ==============================================================
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    
    text: Mapped[str] = mapped_column(nullable=False)
    
    # == Relationships ========================================================
    question: Mapped[Question] = relationship("Question", back_populates="answers")
    
    # == Methods ==============================================================


