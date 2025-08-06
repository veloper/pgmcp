from __future__ import annotations

from typing import TYPE_CHECKING, List, Self, Union

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
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document")

    
    
    # == Hooks ============================================================
    
    async def before_save(self) -> Self:
        """Ensure the document has a title if it is not set."""
        pass
        # if not self.title:
        #     self.title = "Untitled Document"
        #     # try to extract a title from the first section if available
        #     if self.body and isinstance(self.body, Element) and self.body.type == "body":
        #         first_section: Section | None = self.body.children[0] if self.body.children else None
        #         if first_section and first_section.type == "section" and first_section.attributes.get("title"):
        #             self.title = first_section.attributes["title"]
        # return self
    
    async def after_save(self) -> Self:
        """Rebuild the element tree after saving the document."""
        pass
        # from pgmcp.models.element import Element
        # async with Element.async_context() as session:
        #     body = await Element.query().where(document_id=self.id, type="body").first()
        #     if body:
        #         await body.rebuild_tree()
            
        # return self

    # == Methods ==============================================================
    
    
    
    @classmethod
    async def from_markdown(cls, markdown: str, *, corpus_id: int | None = None, title: str | None = None) -> Document:
        chunking_document = ChunkingDocument.from_markdown(markdown)
        return await cls.from_chunking_document(chunking_document, corpus_id=corpus_id, title=title)

    @classmethod
    async def from_html(cls, html: str, *, corpus_id: int | None = None, title: str | None = None) -> Document:
        document = ChunkingDocument.from_html(html)
        return await cls.from_chunking_document(document, corpus_id=corpus_id, title=title)
        
    @classmethod
    async def from_chunking_document(cls, chunking_document: ChunkingDocument, *, corpus_id: int | None = None, title: str | None = None) -> Document:
        """
        Build a Document ORM object tree from an MdDocument, in memory only (no DB/session logic).
        Returns a fully-linked Document object graph.
        """
        from pgmcp.models.chunk import Chunk
        
        
        attrs = {}
        attrs['title'] = title or chunking_document.title
        if corpus_id is not None:
            attrs['corpus_id'] = corpus_id
        
        doc = cls(**attrs)
        
        # Create the chunks and link them to the document
        for chunk in chunking_document.chunks:
            await Chunk.from_chunking_chunk(doc, chunk)
        
        return doc
        
        
        

    #     return doc











