from __future__ import annotations

import datetime

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Self, Type

from blinker import Namespace
from sqlalchemy import DateTime, func, schema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_base, mapped_column
from sqlalchemy.sql.elements import NamedColumn
from sqlalchemy.sql.selectable import Select
from typing_extensions import Literal

from pgmcp.database_connection_settings import DatabaseConnectionSettings
from pgmcp.settings import get_settings


_settings = get_settings()

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
    
# ================================================================
# Base Model Class
# ================================================================    


class Base(DeclarativeBase):
    """Base class for all models in the application."""
    __abstract__ = True

    # == Columns =========================================================

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime.datetime] = mapped_column( DateTime(timezone=True), nullable=False, server_default=func.now() )
    updated_at: Mapped[datetime.datetime] = mapped_column( DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now() )
    
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

    # == Persistence Methods =========================================================

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
        
        async with self.async_session() as session:    
            async with send_async_signal_pair("save", self):
                async with send_async_signal_pair(("insert" if self.is_new else "update"), self):
                    session.add(self)
                    await self.commit()
                    await self.flush()
                    await self.refresh()
                
    
    async def destroy(self):
        """Delete this model instance from the database."""
        async with self.async_session() as session:
            async with send_async_signal_pair("destroy", self):
                await session.delete(self)
                await self.commit() # leave expired so the instance is not in the session anymore
                await self.flush() # immediately flush the session to remove the instance from it so it's more like an AR

    async def commit(self):
        """Commit the current session."""
        async with self.async_session() as session:
            async with send_async_signal_pair("commit", self):
                await session.commit()

    async def refresh(self): 
        """Refresh the model instance from the database."""
        async with self.async_session() as session:
            async with send_async_signal_pair("refresh", self):
                await session.refresh(self)

    async def flush(self): 
        """Flush the current session."""
        async with self.async_session() as session:
            async with send_async_signal_pair("flush", self):
                await session.flush()

    # == Session Management Methods =========================================================

    @classmethod
    @asynccontextmanager
    async def async_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager that yields the context-local AsyncSession.
        Ensures the same session is reused within the same async context.
        """
        session = await _settings.db.get_primary().sqlalchemy_async_session()
        yield session

    @classmethod
    async def get_async_session(cls) -> AsyncSession:
        """Return an AsyncSession that can be used as a context manager."""
        return await _settings.db.get_primary().sqlalchemy_async_session()
    
    @classmethod
    @asynccontextmanager
    async def transaction(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager for a SQLAlchemy async transaction.

        Yields:
            AsyncSession with an active transaction (committed or rolled back on exit).
        """
        async with cls.async_session() as session:
            async with session.begin_nested():
                yield session

    # == Query Building Methods =========================================================

    @classmethod
    async def select(cls: type[Self]) -> Select:
        """Return a SQLAlchemy select statement for the model."""
        return select(cls)

    @classmethod
    async def filter_by(cls: type[Self], *args, **kwargs) -> Select:
        """Return a SQLAlchemy select statement with filters applied."""
        return select(cls).filter(*args, **kwargs)

    @classmethod
    async def get_by_id(cls: type[Self], id: int) -> Self | None:
        """Fetch a record by its primary key (if it's `id`)."""
        async with cls.async_session() as session:
            result = await session.execute(select(cls).where(cls.id == id))
            return result.scalar_one_or_none()

    @classmethod
    async def all(cls: type[Self]) -> list[Self]:
        """Fetch all records for this model."""
        async with cls.async_session() as session:
            result = await session.execute(select(cls))
            return list(result.scalars().all())

    @classmethod
    async def count(cls: type[Self], *args, **kwargs) -> int:
        """Return the count of records matching the filter."""
        async with cls.async_session() as session:
            stmt = select(func.count()).select_from(cls)
            if args or kwargs:
                stmt = stmt.filter(*args, **kwargs)
            result = await session.execute(stmt)
            return result.scalar_one()



