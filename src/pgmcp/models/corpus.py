from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, Awaitable, Callable, List

import openai

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Index

from pgmcp.models.base import Base
from pgmcp.models.chunk import Chunk


if TYPE_CHECKING:
    from pgmcp.models.document import Document
    from pgmcp.models.library import Library


class Corpus(Base):
    # == Model Metadata =======================================================
    __tablename__ = "corpora"
    __table_args__ = (
        Index(
            "ix_corpora_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"}
        ),
    )

    # == Columns ==============================================================
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    library_id: Mapped[int] = mapped_column(ForeignKey("libraries.id"), nullable=False)

    # == Relationships ========================================================
    library: Mapped[Library] = relationship(back_populates="corpora")
    
    documents: Mapped[list[Document]] = relationship("Document", back_populates="corpus", cascade="all, delete-orphan")

    # == Methods ==============================================================

    ProgressCallback = Callable[[List[Chunk], int, int], Awaitable[None]] # (chunks that were updated, chunk_buckets processed, chunk_buckets total)

    async def update_embeddings(self, on_save: ProgressCallback | None = None) -> None:
        """Update embeddings for all chunks in the corpus.
        
        This is a save operation that will update the embeddings for all chunks in the corpus.
        """
        from pgmcp.models.chunk import Chunk
        from pgmcp.models.document import Document
        
        client = openai.AsyncOpenAI()
        
        async with Chunk.async_context() as session:
            chunk_bucket_count = await self.get_chunk_bucket_count()
            bucket_index = 0
            async for chunk_bucket in self.gather_chunk_buckets():
                # Ensure chunks are loaded 
                # Extract text content from chunks
                texts = [chunk.to_embeddable_input() for chunk in chunk_bucket]
                
                # Get embeddings from OpenAI
                try:
                    response = await client.embeddings.create(
                        model="text-embedding-3-small",
                        input=texts
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to get embeddings from OpenAI: {e} on {texts}") from e
                
                # Update chunks with their embeddings
                for i, chunk in enumerate(chunk_bucket):
                    if response and response.data and isinstance(response.data, list) and i < len(response.data) and hasattr(response.data[i], 'embedding') and isinstance(response.data[i].embedding, list):
                        chunk.embedding = response.data[i].embedding
                        await chunk.save()
                    else:
                        raise ValueError(f"Invalid response format or missing embedding for chunk {i} in bucket.")
                
                if on_save:
                    await on_save(chunk_bucket, bucket_index+1, chunk_bucket_count)
                
                bucket_index += 1

    async def get_chunk_bucket_count(self, token_limit: int = 280000) -> int:
        """Use maths to estimate the number of chunk buckets we will have, based on the token limit and queryable information"""
        from pgmcp.models.chunk import Chunk
        from pgmcp.models.document import Document
        
        async with Chunk.async_context() as session:
            query_builder = Chunk.query().select(Chunk.token_count).joins(Chunk.document, Document.corpus).where(Document.corpus_id == self.id)
            records = await query_builder.all()
            
            buckets : List[int] = [0] # Start with one bucket
            for record in records:
                # can fit in bucket?
                if buckets[-1] + record.token_count > token_limit:
                    buckets.append(0) # new bucket
                    
                buckets[-1] += record.token_count
                
            return len(buckets)


    async def gather_chunk_buckets(self, token_limit: int = 280000) -> AsyncGenerator[List[Chunk], None]:
        """Gather chunks from all documents in the corpus, in groups of `token_limit` called buckets
        so we can use them to call embed on this corpus efficiently.
        
        This will act as a generator that yields one bucket at a time.
        """
        from pgmcp.models.chunk import Chunk
        from pgmcp.models.document import Document
        
        async with Chunk.async_context() as session:
        
        
            current_bucket: List[Chunk] = []
            current_token_count = 0        

            query_builder = Chunk.query().joins(Chunk.document, Document.corpus).where(Document.corpus_id == self.id).order(Chunk.id, "asc")

            async for chunk in query_builder.find_each(batch_size=100):
                if current_token_count + chunk.token_count > token_limit:
                    yield current_bucket # Yield the current bucket
                    
                    # Clear and start a new bucket
                    current_bucket = [chunk] 
                    current_token_count = chunk.token_count 
                else:
                    current_bucket.append(chunk)
                    current_token_count += chunk.token_count
            
            # Yield any remaining chunks in the last (under-filled) bucket
            if current_bucket:
                yield current_bucket


