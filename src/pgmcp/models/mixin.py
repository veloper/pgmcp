from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from pgmcp.models.content import Content


if TYPE_CHECKING:
    from pgmcp.models.listing_item import ListingItem
    from pgmcp.models.section import SectionItem


class IsEmbeddableMixin:
    """
    Mixin for models that can be embedded into a Vector 
    
    This mixin adds an `embedding` field to the model, which is a vector representation of the content.
    It's optional, allowing models to be created without an embedding or to discover them for later batching.
    The embedding is typically a 1536-dimensional vector, but this can be adjusted based on the embedding model 
    from OpenAI `text-embedding-3-sm` 
    """
    @declared_attr
    def embedding(cls) -> "Mapped[Vector | None]":
        return mapped_column(Vector(1536), nullable=True)
    

class IsContentableMixin:
    """
    Mixin for models that have_one Content association through a `contentable_type` and `contentable_id` field.
    
    This introduces a `content` relationship that allows accessing the associated Content model. 
    """
    @declared_attr
    def content(cls) -> "Mapped[Content | None]":
        return relationship(
            back_populates="contentable",
            primaryjoin="and_(IsContentableMixin.contentable_id == Content.id, "
                        "IsContentableMixin.contentable_type == 'Content')"
        )


class IsSectionableMixin:
    """
    Mixin for models that have_one SectionItem association through a `sectionable_type` and `sectionable_id` field.
    """
    @declared_attr
    def section_item(cls) -> "Mapped[SectionItem | None]":
        return relationship(
            back_populates="sectionable",
            primaryjoin="and_(IsSectionableMixin.sectionable_id == SectionItem.id, "
                        "IsSectionableMixin.sectionable_type == 'SectionItem')"
        )


class IsListableMixin:
    """
    Mixin for models that have_one ListingItem association through a `listable_type` and `listable_id` field.

    This mixin introduces a `listable` relationship that allows accessing the associated ListingItem model.
    """
    @declared_attr
    def list_item(cls) -> "Mapped[ListingItem | None]":
        return relationship(
            back_populates="listable",
            primaryjoin="and_(IsListableMixin.listing_itemable_id == ListingItem.id, "
                        "IsListableMixin.listing_itemable_type == 'ListingItem')"
        )
