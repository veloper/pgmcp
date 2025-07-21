from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, and_
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship


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
    
    This provides the fields needed for the Content model's generic_relationship.
    Access the content via the Content model's 'contentable' relationship rather than through this mixin.
    """
    @declared_attr
    def contentable_id(cls) -> Mapped[int | None]:
        return mapped_column(Integer, nullable=True)
    
    @declared_attr
    def contentable_type(cls) -> Mapped[str]:
        return mapped_column(String, nullable=False)


class IsSectionableMixin:
    """
    Mixin for models that have_one SectionItem association through a `sectionable_type` and `sectionable_id` field.
    
    This provides the fields needed for relationships. Consider adding explicit relationships 
    in individual models if needed.
    """
    @declared_attr
    def sectionable_id(cls) -> Mapped[int | None]:
        return mapped_column(Integer, nullable=True)
    
    @declared_attr
    def sectionable_type(cls) -> Mapped[str]:
        return mapped_column(String, nullable=False)


class IsListableMixin:
    """
    Mixin for models that have_one ListingItem association through a `listable_type` and `listable_id` field.

    This provides the fields needed for relationships. Consider adding explicit relationships 
    in individual models if needed.
    """
    @declared_attr
    def listable_id(cls) -> Mapped[int | None]:
        return mapped_column(Integer, nullable=True)
    
    @declared_attr
    def listable_type(cls) -> Mapped[str]:
        return mapped_column(String, nullable=False)
