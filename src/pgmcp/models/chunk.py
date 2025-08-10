import json

from typing import TYPE_CHECKING, Any, Dict, List, Self, Union

import tiktoken

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.chunking.chunk import Chunk as ChunkingChunk
from pgmcp.chunking.encodable_chunk import EncodableChunk
from pgmcp.chunking.heredoc_yaml import HeredocYAML
from pgmcp.models.base import Base
from pgmcp.models.base_query_builder import QueryBuilder


cl100k_base_encoder = tiktoken.get_encoding("cl100k_base")

if TYPE_CHECKING:
    from pgmcp.models.document import Document


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        # IVFFlat index for cosine distance
        Index(
            "ix_chunks_embedding_ivfflat_cosine",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"lists": 100},
        ),
    )
    

    id: Mapped[int]                = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int]       = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    content: Mapped[str]           = mapped_column(String, nullable=False)
    token_model: Mapped[str]       = mapped_column(String, nullable=False, default="cl100k_base")
    token_count: Mapped[int]       = mapped_column(Integer, nullable=False)
    meta: Mapped[dict]             = mapped_column(JSONB, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True, doc="Vector embedding of the chunk content")

    # == Relationships ==
    
    document = relationship("Document", back_populates="chunks")
    
    # == Methods ==
    
    def to_embeddable_input(self) -> str:
        """Prepare the chunk content for embedding as YAML with heredocs."""
        envelope = {
            "meta": self.meta or {},
            "content": self.content,
        }
        return HeredocYAML.dump(envelope)

    async def embed(self) -> Self:
        """Generate and store the embedding for this chunk."""
        import openai
        
        client = openai.AsyncOpenAI()
        
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=self.to_embeddable_input(),
            dimensions=1536
        )
        
        self.embedding = response.data[0].embedding
        
        return self
    
    def model_dump_rag(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "meta": self.meta,
            "content": self.content,
        }

    @classmethod
    def cosine_distance(cls, vector: List[float]) -> QueryBuilder[Self]:
        return cls.query().order(Chunk.embedding.cosine_distance(vector))

    @classmethod
    async def from_chunking_chunk(cls, document: Union[int, "Document"], chunk: ChunkingChunk) -> "Chunk":
        """Create a Chunk ORM object from a ChunkingChunk."""
        from pgmcp.models.document import Document
        if isinstance(document, int):
            document = Document(id=document)
            
        if not isinstance(document, Document):
            raise ValueError("document must be an instance of Document or an integer document ID")
                

        # Convert meta to dict safely
        try:
            meta_dict = chunk.meta.model_dump() if chunk.meta else {}
        except (AttributeError, TypeError):
            meta_dict = {}


        partial = cls(
            document=document,
            content=chunk.content,
            meta=meta_dict
        )

        partial.token_model = "cl100k_base"
        partial.token_count = len(cl100k_base_encoder.encode(partial.to_embeddable_input()))

        return partial
