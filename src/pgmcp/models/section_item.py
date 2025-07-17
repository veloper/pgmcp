from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import generic_relationship

from pgmcp.models.base import Base


if TYPE_CHECKING:
    from pgmcp.models.section import Section


class SectionItem(Base):
    """
    Join table: Section has many SectionItems (Paragraph, SubSection, List, Table, CodeBlock, etc)
    SectionItem polymorphically belongs to one of those types.
    """

    # == Model Metadata =======================================================
    __tablename__   = "section_items"
    __mapper_args__ = {
        "polymorphic_on"      : "sectionable_type",
        "polymorphic_identity": "sectionable",
        "with_polymorphic"    : "*",
    }

    # == Columns ==============================================================
    section_id      : Mapped[int] = mapped_column(nullable=False)
    sectionable_type: Mapped[str] = mapped_column(nullable=False)
    sectionable_id  : Mapped[int] = mapped_column(nullable=False)
    position        : Mapped[int] = mapped_column(nullable=False, default=0)

    # == Relationships ========================================================
    section         : Mapped[Section] = relationship("Section", back_populates="section_items")

    # Equivalent To: belongs_to(:sectionable), polymorphic: true 
    sectionable = generic_relationship(
        sectionable_type,
        sectionable_id,
    )

    # == Methods ============================================================== 
    # @property
    # def sectionable(self):
    #     from sqlalchemy.orm import object_session

    #     if not self.sectionable_type or not self.sectionable_id:
    #         return None

    #     cls = self.__class__.registry._class_registry.get(self.sectionable_type)
    #     if isinstance(cls, type):
    #         if session := object_session(self):
    #             return session.get(cls, self.sectionable_id)
    #     return None
