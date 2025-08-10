from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, List, Self, Union

import openai

from bs4 import BeautifulSoup
from sqlalchemy import ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.chunking.document import Document as ChunkingDocument
from pgmcp.models.base import Base


if TYPE_CHECKING:
    from pgmcp.models.chunk import Chunk
    from pgmcp.models.corpus import Corpus


class Document(Base):
    """Represents a document in a corpus.

    Supports Markdown, HTML, and binary formats (e.g., PDF, Word). Documents are chunked for 
    processing and linked to a corpus.
    """
    
    # == Model Metadata =======================================================
    __tablename__ = "documents"

    # == Columns ============================================================== 
    corpus_id    : Mapped[int]          = mapped_column(ForeignKey("corpora.id"), nullable=False)
    title        : Mapped[str | None]   = mapped_column(nullable=True)
    content      : Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, doc="Original binary content of the document, if applicable")
    content_type : Mapped[str | None]   = mapped_column(nullable=True, default="text/plain", doc="MIME type of the original content, if applicable")

    # == Relationships ========================================================
    
    corpus: Mapped[Corpus] = relationship("Corpus", back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    # == Factory Methods ====================================================

    @classmethod
    async def from_markdown(cls, markdown: str, *, corpus_id: int | None = None, title: str | None = None, content: bytes | None = None, content_type: str | None = None) -> Document:
        chunking_document = ChunkingDocument.from_markdown(markdown)
        return await cls.from_chunking_document(chunking_document, corpus_id=corpus_id, title=title, content=content, content_type=content_type)

    @classmethod
    async def from_html(cls, html: str, *, corpus_id: int | None = None, title: str | None = None, content: bytes | None = None, content_type: str | None = None) -> Document:
        document = ChunkingDocument.from_html(html)
        return await cls.from_chunking_document(document, corpus_id=corpus_id, title=title, content=content, content_type=content_type)
        
    @classmethod
    async def from_chunking_document(cls, chunking_document: ChunkingDocument, *, corpus_id: int | None = None, title: str | None = None, content: bytes | None = None, content_type: str | None = None) -> Document:
        """
        Build a Document ORM object tree from an MdDocument, in memory only (no DB/session logic).
        Returns a fully-linked Document object graph.
        """
        from pgmcp.models.chunk import Chunk
        
        
        attrs = {}
        attrs['title']         = chunking_document.title
        attrs['content']       = chunking_document.input_content
        attrs['content_type']  = chunking_document.input_content_type

        # KW Arg Overrides
        if corpus_id is not None:
            attrs['corpus_id'] = corpus_id
        if title is not None:
            attrs['title'] = title
        if content is not None:
            attrs['content'] = content 
        if content_type is not None:
            attrs['content_type'] = content_type 
        
        doc = cls(**attrs)
        
        # Create the chunks and link them to the document
        for chunk in chunking_document.chunks:
            await Chunk.from_chunking_chunk(doc, chunk)
        
        return doc
        
    async def update_embeddings(self) -> None:
        """Update embeddings for all chunks in the corpus.
        
        This is a save operation that will update the embeddings for all chunks in the corpus.
        """
        from pgmcp.models.chunk import Chunk
        client = openai.AsyncOpenAI()
        
        async with Chunk.async_context() as session:
            async for chunk_bucket in self.gather_chunk_buckets():
                # Ensure chunks are loaded 
                # Extract text content from chunks
                texts = [chunk.to_embeddable_input() for chunk in chunk_bucket]

                # Get embeddings from OpenAI
                response = await client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                
                # Update chunks with their embeddings
                for i, chunk in enumerate(chunk_bucket):
                    if response and response.data and isinstance(response.data, list) and i < len(response.data) and hasattr(response.data[i], 'embedding') and isinstance(response.data[i].embedding, list):
                        chunk.embedding = response.data[i].embedding
                        await chunk.save()
                    else:
                        raise ValueError(f"Invalid response format or missing embedding for chunk {i} in bucket.")

    async def gather_chunk_buckets(self, token_limit: int = 280000) -> AsyncGenerator[List["Chunk"], None]:
        """Gather chunks into buckets that can be embedded together without exceeding the token limit."""
        from pgmcp.models.chunk import Chunk
        
        current_bucket = []
        current_token_count = 0
        
        async with Chunk.async_context() as session:
            async for chunk in Chunk.query().where(Chunk.document_id == self.id).find_each(batch_size=100):
                if current_token_count + chunk.token_count > token_limit:
                    if current_bucket:
                        yield current_bucket
                    current_bucket = [chunk]
                    current_token_count = chunk.token_count
                else:
                    current_bucket.append(chunk)
                    current_token_count += chunk.token_count
            
            if current_bucket:
                yield current_bucket




