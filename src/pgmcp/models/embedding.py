from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base


if TYPE_CHECKING:
    from pgmcp.models.chunk import Chunk

class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        Index(
            "ix_embeddings_vector_ivfflat_cosine",
            "vector",
            postgresql_using="ivfflat",
            postgresql_ops={"vector": "vector_cosine_ops"},
            postgresql_with={"lists": 100},
        ),
    )

    # == Columns ==

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    vector: Mapped[List[float]] = mapped_column(Vector(1536), nullable=False, doc="Vector embedding of the chunk content")

    # == Relationships ==
    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="embedding", uselist=False)
