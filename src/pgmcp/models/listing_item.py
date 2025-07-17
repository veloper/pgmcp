from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import generic_relationship

from pgmcp.models.base import Base
from pgmcp.models.mixin import IsContentableMixin


if TYPE_CHECKING:
    from pgmcp.models.listing import Listing

class ListingItem(IsContentableMixin, Base):
    # == Model Metadata =======================================================
    
    __tablename__ = "listing_items"
    __mapper_args__ = {
        "polymorphic_on"      : "listable_type",
        "polymorphic_identity": "listable",
        "with_polymorphic"    : "*",
    }

    # == Columns ============================================================== 
    listing_id    : Mapped[int] = mapped_column(nullable=False)
    position      : Mapped[int] = mapped_column(nullable=False, default=0)
    listable_type : Mapped[str] = mapped_column(nullable=False)
    listable_id   : Mapped[int] = mapped_column(nullable=False)
    
    # == Relationships ========================================================
    listing: Mapped["Listing"] = relationship( "Listing", back_populates="child_listing_items" )
    
    # Equivalent To: belongs_to(:listable), polymorphic: true
    listable = generic_relationship( listable_type, listable_id )
    
    
    # == Methods ==============================================================
