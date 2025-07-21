from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
from pgmcp.models.content import Content
from pgmcp.models.mixin import IsContentableMixin, IsListableMixin, IsSectionableMixin


if TYPE_CHECKING:
    from pgmcp.models.listing_item import ListingItem


class Listing(IsContentableMixin, IsSectionableMixin, IsListableMixin, Base):
    """
    Represents a list in a document, which can contain various types of listing items.
    
    Uses `listing` nomenclature to avoid confusion with `List` type in Python.
    """

    # == Model Metadata =======================================================
    __tablename__ = "listings"

    # == Columns ============================================================== 
    section_item_id: Mapped[int] = mapped_column(ForeignKey("section_items.id"), nullable=False)

    # == Relationships ========================================================
    child_listing_items: Mapped[list["ListingItem"]] = relationship(
        "ListingItem",
        back_populates = "listing",
        cascade       = "all, delete-orphan",
        lazy          = "joined"
    )

    # == Methods ==============================================================
