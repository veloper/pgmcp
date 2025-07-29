from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.orm import Mapped, as_declarative, mapped_column, relationship
from sqlalchemy_declarative_extensions import declarative_database
from sqlalchemy_declarative_extensions.dialects.postgresql import Function

from pgmcp.models.base import Base
from pgmcp.models.document import Document
from pgmcp.models.mixin import IsEmbeddableMixin


class Element(Base, IsEmbeddableMixin):
    __tablename__ = "element"
    __table_args__ = (
        UniqueConstraint("type", "document_id", name="uq_element_type_document_id"),
    )
    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "element"
    }
    
    # == Columns ==============================================================
    
    type        : Mapped[str]         = mapped_column(index=True, nullable=False, comment="Type of the element and discriminator for polymorphic behavior")
    document_id : Mapped[int]         = mapped_column(ForeignKey("documents.id"), nullable=True, comment="Document that this element is a part of")
    parent_id   : Mapped[int | None]  = mapped_column(ForeignKey("element.id"), nullable=True, comment="Parent element that this element is attached to")
    content     : Mapped[str | None]  = mapped_column(TEXT, nullable=True, comment="Text content of the element and all of its children")
    position    : Mapped[int]         = mapped_column(nullable=False, default=0, comment="position of the element among its siblings")
    attributes  : Mapped[dict]        = mapped_column(JSONB, default=dict, comment="JSONB representation of attributes, free form.")

    # Nested Set Model fields
    # These fields are optional and require explicit rebuilding on tree mutation.
    left: Mapped[int | None]  = mapped_column(default=None, comment="Left boundary for tree structure, if applicable")
    level: Mapped[int]        = mapped_column(default=0, comment="Level in the tree structure, if applicable")
    right: Mapped[int | None] = mapped_column(default=None, comment="Right boundary for tree structure, if applicable")
    
    
    children_count: Mapped[int] = mapped_column(default=0, comment="counter cache for len(self.children)")
    
    # == Relationships ========================================================
    
    children    : Mapped[list["Element"]] = relationship( "Element", back_populates="parent", cascade="all, delete-orphan" )
    parent      : Mapped["Element | None"] = relationship( "Element", remote_side=lambda: [Element.id], back_populates="children" )
    document    : Mapped["Document"] = relationship("Document", back_populates="body")

    def __repr__(self) -> str:
        return self._repr_tree(indent=0)

    def _repr_tree(self, indent: int) -> str:
        tabs = "    " * (int(indent) + 1)
        attrs = ", ".join(f"{k}={v!r}" for k, v in (self.attributes.items() if isinstance(self.attributes, dict) else {}))
        representation = f"{tabs}<{self.__class__.__name__} id={self.id}, type={self.type}, document_id={self.document_id}, attributes={{ {attrs} }} left={self.left}, right={self.right}, level={self.level} position={self.position}>"
        representation += "\n" + "\n".join(child._repr_tree(indent + 1) for child in self.children)
        return representation + f"\n{tabs}</{self.__class__.__name__}>"

    

    @classmethod
    async def rebuild_tree(cls, session):
        """Must be called manually, dont try to put in side of a callback as it will be way too slow."""
        async with cls.async_context() as session:
            await session.execute(text("SELECT rebuild_element_tree()"))


class Body(Element):
    __mapper_args__ = {"polymorphic_identity": "body"}

class Section(Element):
    __mapper_args__ = {"polymorphic_identity": "section"}
    
class SectionItem(Element):
    __mapper_args__ = {"polymorphic_identity": "section_item"}

class Sentence(Element):
    __mapper_args__ = {"polymorphic_identity": "sentence"}

class Paragraph(Element):
    __mapper_args__ = {"polymorphic_identity": "paragraph"}

class Listing(Element):
    __mapper_args__ = {"polymorphic_identity": "listing"}
        
class ListingItem(Element):
    __mapper_args__ = {"polymorphic_identity": "list_item"}
    
class CodeBlock(Element):
    __mapper_args__ = {"polymorphic_identity": "code_block"}
    
class Table(Element):
    __mapper_args__ = {"polymorphic_identity": "table"}
    
class TableRow(Element):
    __mapper_args__ = {"polymorphic_identity": "table_row"}
    
class TableRowCell(Element):
    __mapper_args__ = {"polymorphic_identity": "table_row_cell"}
    
class Blockquote(Element):
    __mapper_args__ = {"polymorphic_identity": "blockquote"}
