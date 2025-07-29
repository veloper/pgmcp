from typing import TYPE_CHECKING, Self, Type

from pgvector.sqlalchemy import Vector
from sqlalchemy import TEXT, Integer, String, and_
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship


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
    Mixin for models that have "content" as a field that is of type text and is central to their representation.

    This mixin adds a `content` field to the model, which is typically used to store text data.
    """
    
    @declared_attr
    def content(cls):
        return mapped_column(TEXT, nullable=True)


class IsListableMixin:
    """
    Mixin for models that have_one ListingItem association through a `listable_type` and `listable_id` field.

    This provides the fields needed for relationships. Consider adding explicit relationships 
    in individual models if needed.
    """
    
    @declared_attr
    def listing_item(cls):
        from sqlalchemy import and_
        from sqlalchemy.orm import foreign

        from pgmcp.models.listing_item import ListingItem
        return relationship(
            "ListingItem",
            primaryjoin=lambda: and_(
                foreign(ListingItem.listable_id) == getattr(cls, "id"),
                ListingItem.listable_type == cls.__name__
            ),
            uselist=False,
            cascade="all, delete-orphan",
            overlaps="listing_item"
        )
    

class RailsQueryInterfaceMixin:
    """
    Mixin providing Rails-style query interface helpers for SQLAlchemy models.
    """
    @classmethod
    def query(cls: Type[Self]):
        """Rails: Model.all - returns a QueryBuilder for method chaining"""
        from pgmcp.models.base_query_builder import QueryBuilder
        return QueryBuilder(cls)

    @classmethod
    def where(cls: Type[Self], *args, **kwargs):
        """Rails: Model.where(condition)"""
        return cls.query().where(*args, **kwargs)

    @classmethod
    def order(cls: Type[Self], *args):
        """Rails: Model.order(:column)"""
        return cls.query().order(*args)
    
    @classmethod
    def limit(cls: Type[Self], n: int):
        """Rails: Model.limit(n)"""
        return cls.query().limit(n)

    @classmethod
    def offset(cls: Type[Self], n: int):
        """Rails: Model.offset(n)"""
        return cls.query().offset(n)

    @classmethod
    def distinct(cls: Type[Self], *columns):
        """Rails: Model.distinct"""
        return cls.query().distinct(*columns)

    @classmethod
    def select_columns(cls: Type[Self], *columns):
        """Rails: Model.select(:column1, :column2)"""
        return cls.query().select(*columns)

    @classmethod
    def group(cls: Type[Self], *columns):
        """Rails: Model.group(:column)"""
        return cls.query().group(*columns)

    @classmethod
    def group_by(cls: Type[Self], *columns):
        """Alias for group()"""
        return cls.query().group_by(*columns)

    @classmethod
    def having(cls: Type[Self], *conditions):
        """Rails: Model.having(condition)"""
        return cls.query().having(*conditions)

    @classmethod
    def joins(cls: Type[Self], *relationships):
        """Rails: Model.joins(:association)"""
        return cls.query().joins(*relationships)

    @classmethod
    def left_joins(cls: Type[Self], *relationships):
        """Rails: Model.left_joins(:association)"""
        return cls.query().left_joins(*relationships)

    @classmethod
    def includes(cls: Type[Self], *relationships):
        """Rails: Model.includes(:association)"""
        return cls.query().includes(*relationships)

    @classmethod
    def preload(cls: Type[Self], *relationships):
        """Rails: Model.preload(:association)"""
        return cls.query().preload(*relationships)

    @classmethod
    def eager_load(cls: Type[Self], *relationships):
        """Rails: Model.eager_load(:association)"""
        return cls.query().eager_load(*relationships)

    @classmethod
    def readonly(cls: Type[Self]):
        """Rails: Model.readonly"""
        return cls.query().readonly()

    @classmethod
    def lock(cls: Type[Self], mode: str = "UPDATE"):
        """Rails: Model.lock"""
        return cls.query().lock(mode)

    @classmethod
    def none(cls: Type[Self]):
        """Rails: Model.none"""
        return cls.query().none()

    @classmethod
    async def find_by(cls: Type[Self], **kwargs):
        """Rails: Model.find_by(attribute: value)"""
        return await cls.query().find_by(**kwargs)

    @classmethod
    async def find_by_or_raise(cls: Type[Self], **kwargs):
        """Rails: Model.find_by!(attribute: value)"""
        return await cls.query().find_by_or_raise(**kwargs)

    @classmethod
    async def exists(cls: Type[Self], **kwargs):
        """Rails: Model.exists?(conditions)"""
        return await cls.query().exists(**kwargs)

    @classmethod
    async def take(cls: Type[Self], n: int | None = None):
        """Rails: Model.take or Model.take(n)"""
        return await cls.query().take(n)

    @classmethod
    async def first(cls: Type[Self], n: int | None = None) -> Self | None | list[Self]:
        """Rails: Model.first or Model.first(n)"""
        return await cls.query().first(n)

    @classmethod
    async def last(cls: Type[Self], n: int | None = None) -> Self | None | list[Self]:
        """Rails: Model.last or Model.last(n)"""
        return await cls.query().last(n)

    @classmethod
    async def count(cls: Type[Self]):
        """Rails: Model.count - count all records"""
        return await cls.query().count()

    @classmethod
    async def pluck(cls: Type[Self], *columns):
        """Rails: Model.pluck(:column1, :column2)"""
        return await cls.query().pluck(*columns)

    @classmethod
    async def ids(cls: Type[Self]):
        """Rails: Model.ids"""
        return await cls.query().ids()

    @classmethod
    async def all(cls: Type[Self]):
        """Rails: Model.all - fetch all records"""
        return await cls.query().all()


