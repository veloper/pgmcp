from __future__ import annotations

import datetime

from collections import UserList
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import (TYPE_CHECKING, Any, AsyncGenerator, Callable, Dict, Generator, List, Optional, Self, Type, TypeVar,
                    Union)

from blinker import Namespace
from sqlalchemy import DateTime, and_, func, schema, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (DeclarativeBase, InstrumentedAttribute, Mapped, Session, declarative_base, mapped_column,
                            sessionmaker)
from sqlalchemy.sql.elements import NamedColumn
from sqlalchemy.sql.selectable import Select
from typing_extensions import Literal

from pgmcp.database_connection_settings import DatabaseConnectionSettings
# from pgmcp.models.base_functions import functions  # TODO: Fix this import
from pgmcp.models.mixin import RailsQueryInterfaceMixin
from pgmcp.settings import get_settings


if TYPE_CHECKING:
    from pgmcp.models.base_query_builder import QueryBuilder


# Sentinel ContextVar for session and ownership
_async_session_ctx: ContextVar[AsyncSession | None] = ContextVar("_async_session_ctx", default=None)
_async_session_owner_ctx: ContextVar[bool] = ContextVar("_async_session_owner_ctx", default=False)

# ================================================================
# Events / Signals
# ================================================================

model_signals = Namespace()

before_save_signal = model_signals.signal("before_save")
after_save_signal = model_signals.signal("after_save")

before_refresh_signal = model_signals.signal("before_refresh")
after_refresh_signal = model_signals.signal("after_refresh")

before_commit_signal = model_signals.signal("before_commit")
after_commit_signal = model_signals.signal("after_commit")

before_flush_signal = model_signals.signal("before_flush")
after_flush_signal = model_signals.signal("after_flush")

before_insert_signal = model_signals.signal("before_insert")
after_insert_signal = model_signals.signal("after_insert")

before_update_signal = model_signals.signal("before_update")
after_update_signal = model_signals.signal("after_update")

before_destroy_signal = model_signals.signal("before_destroy")
after_destroy_signal = model_signals.signal("after_destroy")


@before_save_signal.connect
async def handle_before_save(sender: Base, **kwargs):
    if hasattr(sender, '_before_save') and (before_save := getattr(sender, '_before_save', None)):
        await before_save()

@after_save_signal.connect
async def handle_after_save(sender: Base, **kwargs):
    if hasattr(sender, '_after_save') and (after_save := getattr(sender, '_after_save', None)):
        await after_save()

@before_refresh_signal.connect
async def handle_before_refresh(sender: Base, **kwargs):
    if hasattr(sender, '_before_refresh') and (before_refresh := getattr(sender, '_before_refresh', None)):
        await before_refresh()

@after_refresh_signal.connect            
async def handle_after_refresh(sender: Base, **kwargs):
    if hasattr(sender, '_after_refresh') and (after_refresh := getattr(sender, '_after_refresh', None)):
        await after_refresh()
    
@before_flush_signal.connect
async def handle_before_flush(sender: Base, **kwargs):
    if hasattr(sender, '_before_flush') and (before_flush := getattr(sender, '_before_flush', None)):
        await before_flush()    
            
@after_flush_signal.connect
async def handle_after_flush(sender: Base, **kwargs):
    if hasattr(sender, '_after_flush') and (after_flush := getattr(sender, '_after_flush', None)):
        await after_flush()

@before_commit_signal.connect
async def handle_before_commit(sender: Base, **kwargs):
    if hasattr(sender, '_before_commit') and (before_commit := getattr(sender, '_before_commit', None)):
        await before_commit()

@after_commit_signal.connect
async def handle_after_commit(sender: Base, **kwargs):
    if hasattr(sender, '_after_commit') and (after_commit := getattr(sender, '_after_commit', None)):
        await after_commit()

@before_insert_signal.connect
async def handle_before_insert(sender: Base, **kwargs):
    if hasattr(sender, '_before_insert') and (before_insert := getattr(sender, '_before_insert', None)):
        await before_insert()

@after_insert_signal.connect
async def handle_after_insert(sender: Base, **kwargs):
    if hasattr(sender, '_after_insert') and (after_insert := getattr(sender, '_after_insert', None)):
        await after_insert()

@before_update_signal.connect
async def handle_before_update(sender: Base, **kwargs):
    if hasattr(sender, '_before_update') and (before_update := getattr(sender, '_before_update', None)):
        await before_update()

@after_update_signal.connect
async def handle_after_update(sender: Base, **kwargs):
    if hasattr(sender, '_after_update') and (after_update := getattr(sender, '_after_update', None)):
        await after_update()

@before_destroy_signal.connect
async def handle_before_destroy(sender: Base, **kwargs):
    if hasattr(sender, '_before_destroy') and (before_destroy := getattr(sender, '_before_destroy', None)):
        await before_destroy()

@after_destroy_signal.connect
async def handle_after_destroy(sender: Base, **kwargs):
    if hasattr(sender, '_after_destroy') and (after_destroy := getattr(sender, '_after_destroy', None)):
        await after_destroy()


@asynccontextmanager
async def send_async_signal_pair(signal_name: str, sender: Base) -> AsyncGenerator[None, None]:
    """Context manager that sends the signals by name before an after an operation via context manager."""
    signal_before = model_signals.signal(f"before_{signal_name}")
    signal_after = model_signals.signal(f"after_{signal_name}")

    try:
        await signal_before.send_async(sender)
        yield
    finally:
        await signal_after.send_async(sender)
        
@contextmanager
def send_signal_pair(signal_name: str, sender: Base) -> Generator[None, None, None]:
    """Context manager that sends the signals by name before an after an operation via context manager."""
    signal_before = model_signals.signal(f"before_{signal_name}")
    signal_after = model_signals.signal(f"after_{signal_name}")

    try:
        signal_before.send(sender)
        yield
    finally:
        signal_after.send(sender)
    

# ================================================================
# Base Model Class
# ================================================================    

class Base(DeclarativeBase, RailsQueryInterfaceMixin):
    """Base class for all models in the application."""
    __abstract__ = True

    # == Columns =========================================================

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime.datetime] = mapped_column( DateTime(timezone=True), nullable=False, server_default=func.now() )
    updated_at: Mapped[datetime.datetime] = mapped_column( DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now() )
  
    # == Relationships Helpers =========================================================
    
    async def ensure_loaded(self, *relationships: str) -> Self:
        """Load relationships in place, modifying the current instance."""
        if relationships:
            async with self.async_context() as session:
                await session.refresh(self, attribute_names=relationships)
        return self
  
    # == Hooks ========================================================================
    
    async def _before_save(self): pass
    async def _after_save(self): pass
    
    async def _before_insert(self): pass
    async def _after_insert(self): pass
    
    async def _before_update(self): pass
    async def _after_update(self): pass
    
    async def _before_destroy(self): pass
    async def _after_destroy(self): pass
    
    async def _before_refresh(self): pass
    async def _after_refresh(self): pass
    
    async def _before_commit(self): pass
    async def _after_commit(self): pass
    
    async def _before_flush(self): pass
    async def _after_flush(self): pass

    # == Helpers =====================================================================

    @property
    def primary_key_columns(self) -> List[NamedColumn[Any]]: return list(self.__table__.primary_key)
    
    @property
    def primary_key_column_names(self) -> List[str]: return [col.name for col in self.__table__.primary_key]

    @property
    def primary_key_values(self) -> List[Any]: return [getattr(self, col.name) for col in self.primary_key_columns]
    
    @property
    def is_new(self) -> bool: return any(value is None for value in self.primary_key_values)
    
    @property
    def is_existing(self) -> bool: return not self.is_new


    # == ASYNC Persistence Methods =========================================================

    async def save(self):
        """Active record dumb save method.
        
        This will not work on nested models as you'd need to setup the proper
        traversal to save from leaf to root. This would involve using annotations
        to discover the relationships and save them in the correct order.
        
        While this is possible, for now we're going with simple save and refresh methods.
        
        ---
        
        Events:
        
            1. before_save
                2. before_(insert|update)
                    3. before_commit
                    4. after_commit
                    5. before_flush
                    6. after_flush
                    7. before_refresh
                    8. after_refresh
                9. after_(insert|update)
            10. after_save
            
            
        """
        
        async with self.async_context() as session:    
            async with send_async_signal_pair("save", self):
                async with send_async_signal_pair(("insert" if self.is_new else "update"), self):
                    session.add(self)
                    await self.commit()
                    await self.flush()
                    await self.refresh()
                
    
    async def destroy(self):
        """Delete this model instance from the database."""
        async with self.async_context() as session:
            async with send_async_signal_pair("destroy", self):
                await session.delete(self)
                await self.commit() # leave expired so the instance is not in the session anymore
                await self.flush() # immediately flush the session to remove the instance from it so it's more like an AR

    async def commit(self):
        """Commit the current session."""
        async with self.async_context() as session:
            async with send_async_signal_pair("commit", self):
                await session.commit()

    async def refresh(self): 
        """Refresh the model instance from the database."""
        async with self.async_context() as session:
            async with send_async_signal_pair("refresh", self):
                # Check if `self` is not in the session, and if that is the case, add it before refreshing
                if self not in session:
                    session.add(self)
                await session.refresh(self)

    async def flush(self): 
        """Flush the current session."""
        async with self.async_context() as session:
            async with send_async_signal_pair("flush", self):
                await session.flush()

    # == ASYNC Session Management Methods =========================================================
    @classmethod
    async def open_async_session(cls) -> AsyncSession:
        """
        Explicitly open and set the async session context for notebook use _only_
        """
        session = _async_session_ctx.get()
        if session is None:
            session = await get_settings().db.get_primary().sqlalchemy_async_session()
            _async_session_ctx.set(session)
            _async_session_owner_ctx.set(True)
        return session

    @classmethod
    async def close_async_session(cls):
        """
        Explicitly close and clean up the async session context for notebook use _only_.
        """
        session = _async_session_ctx.get()
        is_owner = _async_session_owner_ctx.get()
        if session and is_owner:
            await session.close()
            _async_session_ctx.set(None)
            _async_session_owner_ctx.set(False)


    @classmethod
    @asynccontextmanager
    async def async_context(cls) -> AsyncGenerator[AsyncSession, None]:
        """Context manager that is the high level unit of operational work spanning multiple AR operations.
        
        This has an explicit close call that release the session back to the pool.
        
        Model usage requires this to be performed at a high level within the application's request/response cycle.
        
        Usage:

        ```python
        async with Model.context() as models:
            await CrawlItem.create(
                url="https://example.com",
                title="Example Crawl Item"
            )
            
            # Perform other operations within the same session
            # no matter how deep in the stack you are, as long
            # as you used this, your models will work.
            def request_handler():
                # This can be any function that needs to use the models
                model = await models.CrawlItem.find(1)

            await models.CrawlItem.update_all({"title": "Updated Title"}, id=1)
        ```
        """
        session = _async_session_ctx.get()
        is_owner = False
        if session is None:
            async with cls._async_session() as session:
                token = _async_session_ctx.set(session)
                owner_token = _async_session_owner_ctx.set(True)
                is_owner = True
                try:
                    yield session
                finally:
                    if is_owner:
                        _async_session_ctx.reset(token)
                        _async_session_owner_ctx.reset(owner_token)
                        # Close the session if we are the owner
                        await session.close()
        else:
            # Nesting within an existing session, just yield but dont close it
            yield session

    @classmethod
    @asynccontextmanager
    async def _async_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager that yields the context-local AsyncSession.
        Ensures the same session is reused within the same async context.
        """
        session = await get_settings().db.get_primary().sqlalchemy_async_session()
        yield session

    # @classmethod
    # async def get_async_session(cls) -> AsyncSession:
    #     """Return an AsyncSession that can be used as a context manager."""
    #     return await _settings.db.get_primary().sqlalchemy_async_session()
    
    @classmethod
    @asynccontextmanager
    async def async_transaction(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager for a SQLAlchemy async transaction.

        Yields:
            AsyncSession with an active transaction (committed or rolled back on exit).
        """
        async with cls.async_context() as session:
            async with session.begin_nested():
                yield session

    # == Query Building Methods =========================================================

    @classmethod
    async def select(cls: type[Self]) -> Select[tuple[Self]]:
        """Return a SQLAlchemy select statement for the model."""
        return select(cls)

    @classmethod
    async def filter_by(cls: type[Self], *args, **kwargs) -> Select[tuple[Self]]:
        """Return a SQLAlchemy select statement with filters applied."""
        return select(cls).filter(*args, **kwargs)

    @classmethod
    async def find(cls: type[Self], id: int) -> Self | None:
        """Fetch a record by its primary key (if it's `id`)."""
        async with cls.async_context() as session:
            result = await session.execute(select(cls).where(cls.id == id))
            return result.scalar_one_or_none()

    
    
    # =======================================================================================
    # AFD: Additional Field Data
    # - When additional fields are added to select(...) SQLAlchemy by default will prevent
    #   the model instance from being returned via scalar_* methods -- instead returning a row.
    # - This approach allows us to handle cases where this happens by stashing the additional fields
    #   in an `additional_fields` attribute within the model instance.
    #
    # Use this to gain access to the additional fields you might have added to aggregate some other
    # information or data from a join.
    #
    # =======================================================================================

    @classmethod
    async def hydrate(cls: type[Self], **kwargs: Any) -> Self:
        """Hydrate a model instance with additional fields."""
        instance = cls(**kwargs)
        instance.additional_fields = {k: v for k, v in kwargs.items() if k not in instance.__table__.columns}
        return instance

    # == AFD Property Implementation =========================================================

    @property
    def additional_fields(self) -> Dict[str, Any]:
        """Return additional field data stored in the model instance."""
        if not hasattr(self, '_additional_fields'):
            setattr(self, '_additional_fields', {})
        return getattr(self, '_additional_fields')
    
    @additional_fields.setter
    def additional_fields(self, value: Dict[str, Any]):
        """Set additional field data in the model instance."""
        if not hasattr(self, '_additional_fields'):
            setattr(self, '_additional_fields', {})
        self.additional_fields.update(value)
        
    @additional_fields.deleter
    def additional_fields(self):
        """Delete additional field data from the model instance."""
        if hasattr(self, '_additional_fields'):
            delattr(self, '_additional_fields') 
    
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializer that can and should be overridden to return a dictionary representation of the model instance."""
        model_fields = {col.name: getattr(self, col.name) for col in self.__table__.columns}
        model_fields.update(self.additional_fields)
        return model_fields


    def get_instrumented_attributes(self) -> Dict[str, InstrumentedAttribute]:
        """Return a dictionary of instrumented attributes for the model."""
        return {attr: getattr(self.__class__, attr) for attr in dir(self.__class__) if isinstance(getattr(self.__class__, attr), InstrumentedAttribute)}
    
    def get_instrumented_attribute_values(self) -> Dict[str, Any]:
        """Return a dictionary of instrumented attribute values for the model."""
        return {attr: getattr(self, attr) for attr in self.get_instrumented_attributes()}

    def model_dump(self, 
        filter: Callable[[str, Any], bool] | None = None,
        exclude: set[str] | None = None,
        exclude_none: bool = True,
    ) -> Dict[str, Any]:
        """Serialize the model to a dict, optionally filtering fields and excluding None values.
        
        This explicitly handles the additional fields and allows for custom filtering to manage the final form.
        """

        all_data = self.get_instrumented_attribute_values()
        all_data.update(self.additional_fields)
        data = {}
        for key, value in all_data.items():
            if exclude and key in exclude:
                continue
            if filter and not filter(key, value):
                continue
            if exclude_none and value is None:
                continue
            data[key] = value
        
        return data
