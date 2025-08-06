from typing import TYPE_CHECKING, Union

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.chunking.chunk import Chunk as ChunkingChunk
from pgmcp.chunking.encodable_chunk import EncodableChunk
from pgmcp.models.base import Base


if TYPE_CHECKING:
    from pgmcp.models.document import Document

class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int]                = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int]       = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    content: Mapped[str]           = mapped_column(String, nullable=False)
    token_model: Mapped[str]       = mapped_column(String, nullable=False, default="cl100k_base")
    token_count: Mapped[int]       = mapped_column(Integer, nullable=False)
    meta: Mapped[dict]             = mapped_column(JSONB, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)

    # == Relationships ==
    
    document = relationship("Document", back_populates="chunks")

    @classmethod
    async def from_chunking_chunk(cls, document: Union[int, "Document"], chunk: ChunkingChunk) -> "Chunk":
        """Create a Chunk ORM object from a ChunkingChunk."""
        from pgmcp.models.document import Document
        encodable_chunk : EncodableChunk = chunk.to_encodable_chunk()

        if isinstance(document, int):
            document = Document(id=document)
            
        if not isinstance(document, Document):
            raise ValueError("document must be an instance of Document or an integer document ID")
        

        # Convert meta to dict safely
        try:
            meta_dict = chunk.meta.model_dump() if chunk.meta else {}
        except (AttributeError, TypeError):
            meta_dict = {}

        return cls(
            document=document,
            content=encodable_chunk.content,
            token_model=encodable_chunk.model,
            token_count=encodable_chunk.token_count,
            meta=meta_dict
        )
