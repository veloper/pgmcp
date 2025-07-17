from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgmcp.models.base import Base
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
    section_item_id: Mapped[int] = mapped_column(nullable=False)

    # == Relationships ========================================================
    child_listing_items: Mapped[list["ListingItem"]] = relationship(
        "ListingItem",
        back_populates = "list",
        cascade       = "all, delete-orphan",
        lazy          = "joined"
    )

    parent_listing_item: Mapped["ListingItem | None"] = relationship(
        "ListingItem",
        back_populates = "child_listing_items",
        uselist        = False,
        lazy           = "joined"
    )

    # == Methods ==============================================================
