from __future__ import annotations

from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsEmbeddableMixin


if TYPE_CHECKING:
    from pgmcp.models.content import Content
    from pgmcp.models.question import Question

class Answer(IsEmbeddableMixin, Base):
    """Represents an answer, derived from a piece of content, that serves as a response to a specific question."""
    # == Model Metadata =======================================================
    __tablename__ = "answers"
    
    # == Columns ============================================================== 
    content_id: Mapped[int] = mapped_column(nullable=False)
    question_id: Mapped[int] = mapped_column(nullable=False)
    
    text: Mapped[str] = mapped_column(nullable=False)
    
    # == Relationships ========================================================
    question: Mapped[Question] = relationship("Question", back_populates="answers")
    content: Mapped[Content] = relationship("Content")
    
    # == Methods ==============================================================
