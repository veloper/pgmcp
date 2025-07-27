from __future__ import annotations

from typing import TYPE_CHECKING, List, Self

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from unstructured.documents.elements import Element
from unstructured.partition.html import partition_html

from pgmcp.markdown_document import MdCodeBlock, MdDocument, MdListing, MdListingItem, MdParagraph, MdSection, MdTable
from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin


if TYPE_CHECKING:
    from pgmcp.models.corpus import Corpus
    from pgmcp.models.section import Section


class Document(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    __tablename__ = "documents"

    # == Columns ============================================================== 
    corpus_id: Mapped[int] = mapped_column(ForeignKey("corpora.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(nullable=True)
    
    # == Relationships ========================================================
    corpus: Mapped[Corpus] = relationship("Corpus", back_populates="documents")
    
    sections: Mapped[list[Section]] = relationship(
        "Section", back_populates="document", cascade="all, delete-orphan", lazy="joined"
    )

    # == Methods ==============================================================

        
    
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
        from pgmcp.models.code_block import CodeBlock
        from pgmcp.models.content import Content
        from pgmcp.models.listing import Listing
        from pgmcp.models.listing_item import ListingItem
        from pgmcp.models.paragraph import Paragraph
        from pgmcp.models.section import Section
        from pgmcp.models.section_item import SectionItem
        from pgmcp.models.sentence import Sentence
        from pgmcp.models.table import Table
        from pgmcp.models.table_cell import TableCell
        from pgmcp.models.table_row import TableRow
        
        def build_listing(md_listing):
            listing = Listing(ordered=md_listing.ordered)
            listing.child_listing_items = []
            for idx, item in enumerate(md_listing.listing_items):
                if isinstance(item, MdListing):
                    # Nested list: recurse and attach as listable
                    child_listing = build_listing(item)
                    listing_item = ListingItem(
                        content=Content(text=(item.text if item.text else "")),
                        listing=listing,
                        position=idx,
                        listable=child_listing
                    )
                    listing.child_listing_items.append(listing_item)
                elif isinstance(item, MdListingItem):
                    # Leaf item: create a single ListingItem, not double-wrapped
                    listing_item = ListingItem(
                        content=Content(text=(item.text if item.text else "")),
                        listing=listing,
                        position=idx
                    )
                    listing.child_listing_items.append(listing_item)
            return listing

        def build_section(md_section):
            section = Section(title=md_section.title, content=md_section.text)
            for idx, item in enumerate(md_section.section_items):
                if isinstance(item, MdSection):
                    # Recurse (section, within a SectionItem)
                    child_section = build_section(item)
                    section_item = SectionItem(section=section, sectionable=child_section, position=idx)
                    section.section_items.append(section_item)
                elif isinstance(item, MdParagraph):
                    paragraph = Paragraph(
                        content=Content(text=(item.text if item.text else "")),
                        sentences=[Sentence(text=x.text) for x in item.sentences] 
                    )
                    section_item = SectionItem(section=section, sectionable=paragraph, position=idx)
                    section.section_items.append(section_item)
                elif isinstance(item, MdListing):
                    listing = build_listing(item)
                    section_item = SectionItem(section=section, sectionable=listing, position=idx)
                    section.section_items.append(section_item)
                elif isinstance(item, MdTable):
                    table = Table(
                        content=Content(text=(item.text if item.text else "")),
                        table_rows=[
                            TableRow(
                                content=Content(text=(row.text if row.text else "")),
                                cells=[TableCell(content=Content(text=cell.text)) for cell in row.cells]
                            ) for row in item.table_rows
                        ]
                    )
                    section_item = SectionItem(section=section, sectionable=table, position=idx)
                    section.section_items.append(section_item)
                elif isinstance(item, MdCodeBlock):
                    code_block = CodeBlock(
                        content=Content(text=(item.text if item.text else "")),
                        language_id=item.language_id
                    )
                    section_item = SectionItem(section=section, sectionable=code_block, position=idx)
                    section.section_items.append(section_item)                    
                else:
                    # Handle unexpected item types
                    raise ValueError(f"Unsupported section item type: {type(item)}")
            
            return section

        attrs = {}
        attrs['title'] = md_document.title or title or None
        if corpus_id is not None:
            attrs['corpus_id'] = corpus_id
        doc = cls(**attrs)
        doc.sections = []
        for md_section in md_document.sections:
            section = build_section(md_section)
            doc.sections.append(section)
        return doc
