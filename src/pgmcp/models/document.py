from __future__ import annotations

from typing import TYPE_CHECKING, List, Self, Union

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.markdown_document import (MdCodeBlock, MdDocument, MdListing, MdParagraph, MdSection, MdSentence, MdTable,
                                     MdTableRow, MdTableRowCell)
from pgmcp.models.base import Base
from pgmcp.models.base_query_builder import QueryBuilder
from pgmcp.models.mixin import IsContentableMixin


MdTypes = Union[
    MdDocument,
    MdSection,
    MdParagraph,
    MdListing,
    MdTable,
    MdCodeBlock,
    MdSentence,
    MdListing,
    MdTableRow,
    MdTableRowCell,
]

if TYPE_CHECKING:
    from pgmcp.models.corpus import Corpus
    from pgmcp.models.element import Element
    from pgmcp.models.section import Section


class Document(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__ = "documents"

    # == Columns ============================================================== 
    corpus_id: Mapped[int] = mapped_column(ForeignKey("corpora.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(nullable=True)
    
    # == Relationships ========================================================
    corpus: Mapped[Corpus] = relationship("Corpus", back_populates="documents")

    
    body: Mapped["Element | None"] = relationship(
        "Element",
        primaryjoin="and_(Element.type == 'body', foreign(Element.document_id) == Document.id)",
        uselist=False,
        lazy="joined",
        back_populates="document"
    )

    # == Methods ==============================================================
    
    @classmethod
    def query_eager_loaded(cls, depth: int = 20) -> QueryBuilder["Document"]:
        children = [Element.children] * depth        
        return Document.query().eager_load_chain( Document.body, *children )
    
    @classmethod
    async def from_markdown(cls, markdown: str, *, corpus_id: int | None = None, title: str | None = None) -> Document:
        from pgmcp.utils import convert_markdown_to_markdown_document
        md_document = convert_markdown_to_markdown_document(markdown)
        return await cls.from_markdown_document(md_document, corpus_id=corpus_id, title=title)

    @classmethod
    async def from_html(cls, html: str, *, corpus_id: int | None = None, title: str | None = None) -> Document:
        from pgmcp.utils import convert_html_to_markdown_document
        md_document = convert_html_to_markdown_document(html)
        return await cls.from_markdown_document(md_document, corpus_id=corpus_id, title=title)


    @classmethod
    async def from_markdown_document(cls, md_document: MdDocument, *, corpus_id: int | None = None, title: str | None = None) -> 'Document':
        """
        Build a Document ORM object tree from an MdDocument, in memory only (no DB/session logic).
        Returns a fully-linked Document object graph.
        """
        from pgmcp.models.element import Element

        

        def add_element(md_element: MdTypes, parent: Element | None, doc : Document | None = None) -> Element | None:
            if isinstance(md_element, MdDocument):
                element = Element(type="body", content=md_element.text, document=doc)
                if sections := md_element.sections:
                    for md_section in sections:
                        add_element(md_section, parent=element)
                return element # the only element that can be returned as body
            elif isinstance(md_element, MdSection):
                element = Element(type="section", parent=parent, content=md_element.text, attributes={"title": md_element.title})
                if section_items := md_element.section_items:
                    for md_section_item in section_items:
                        add_element(md_section_item, parent=element)
            elif isinstance(md_element, MdParagraph):
                element = Element(type="paragraph", parent=parent, content=md_element.text)
                if sentences := md_element.sentences:
                    for md_sentence in sentences:
                        add_element(md_sentence, parent=element)
            elif isinstance(md_element, MdSentence):
                element = Element(type="sentence", parent=parent, content=md_element.text)
            elif isinstance(md_element, MdListing):
                element = Element(type="listing", parent=parent, content=md_element.text)
                if listing_items := md_element.listing_items:
                    for md_listing_item in listing_items:
                        add_element(md_listing_item, parent=element)
            elif isinstance(md_element, MdTable):
                element = Element(type="table", parent=parent, content=md_element.text)
                for md_table_row in md_element.table_rows:
                    add_element(md_table_row, parent=element)
            elif isinstance(md_element, MdTableRow):
                element = Element(type="table_row", parent=parent, content=md_element.text)
                for md_table_row_cell in md_element.cells:
                    add_element(md_table_row_cell, parent=element)
            elif isinstance(md_element, MdTableRowCell):
                element = Element(type="table_row_cell", parent=parent, content=md_element.text)
            elif isinstance(md_element, MdCodeBlock):
                element = Element(type="code_block", parent=parent, content=md_element.text,attributes={ "delimiter": md_element.delimiter, "language_id": md_element.language_id })
            else:
                raise ValueError(f"Unsupported markdown element type: {type(md_element)}")
            return None
        

        attrs = {}
        attrs['title'] = md_document.title or title or None
        if corpus_id is not None:
            attrs['corpus_id'] = corpus_id
        # Set contentable_type for IsContentableMixin
        doc = cls(**attrs)
        
        doc.body = add_element(md_document, parent=None, doc=doc)

        return doc











