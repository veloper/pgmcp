from __future__ import annotations

import datetime

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Self, Type

from blinker import Namespace
from sqlalchemy import DateTime, MetaData, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, registry, sessionmaker
from sqlalchemy.sql.elements import NamedColumn

from pgmcp.settings import get_settings


settings = get_settings()

session_ctx: ContextVar[Session | None] = ContextVar("session_ctx", default=None)
session_owner_ctx: ContextVar[bool] = ContextVar("session_owner_ctx", default=False)

# ================================================================
# Setup SQLAlchemy idiomatically and with separate models from default registry and metadata
# ================================================================
scrapy_metadata = MetaData()
scrapy_registry = registry(metadata=scrapy_metadata)

ScrapyBase: Type[DeclarativeBase] = scrapy_registry.generate_base()




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
def handle_before_save(sender: Base, **kwargs):
    if hasattr(sender, '_before_save') and (before_save := getattr(sender, '_before_save', None)):
        before_save()

@after_save_signal.connect
def handle_after_save(sender: Base, **kwargs):
    if hasattr(sender, '_after_save') and (after_save := getattr(sender, '_after_save', None)):
        after_save()

@before_refresh_signal.connect
def handle_before_refresh(sender: Base, **kwargs):
    if hasattr(sender, '_before_refresh') and (before_refresh := getattr(sender, '_before_refresh', None)):
        before_refresh()

@after_refresh_signal.connect            
def handle_after_refresh(sender: Base, **kwargs):
    if hasattr(sender, '_after_refresh') and (after_refresh := getattr(sender, '_after_refresh', None)):
        after_refresh()
    
@before_flush_signal.connect
def handle_before_flush(sender: Base, **kwargs):
    if hasattr(sender, '_before_flush') and (before_flush := getattr(sender, '_before_flush', None)):
        before_flush()    
            
@after_flush_signal.connect
def handle_after_flush(sender: Base, **kwargs):
    if hasattr(sender, '_after_flush') and (after_flush := getattr(sender, '_after_flush', None)):
        after_flush()

@before_commit_signal.connect
def handle_before_commit(sender: Base, **kwargs):
    if hasattr(sender, '_before_commit') and (before_commit := getattr(sender, '_before_commit', None)):
        before_commit()

@after_commit_signal.connect
def handle_after_commit(sender: Base, **kwargs):
    if hasattr(sender, '_after_commit') and (after_commit := getattr(sender, '_after_commit', None)):
        after_commit()

@before_insert_signal.connect
def handle_before_insert(sender: Base, **kwargs):
    if hasattr(sender, '_before_insert') and (before_insert := getattr(sender, '_before_insert', None)):
        before_insert()

@after_insert_signal.connect
def handle_after_insert(sender: Base, **kwargs):
    if hasattr(sender, '_after_insert') and (after_insert := getattr(sender, '_after_insert', None)):
        after_insert()

@before_update_signal.connect
def handle_before_update(sender: Base, **kwargs):
    if hasattr(sender, '_before_update') and (before_update := getattr(sender, '_before_update', None)):
        before_update()

@after_update_signal.connect
def handle_after_update(sender: Base, **kwargs):
    if hasattr(sender, '_after_update') and (after_update := getattr(sender, '_after_update', None)):
        after_update()

@before_destroy_signal.connect
def handle_before_destroy(sender: Base, **kwargs):
    if hasattr(sender, '_before_destroy') and (before_destroy := getattr(sender, '_before_destroy', None)):
        before_destroy()

@after_destroy_signal.connect
def handle_after_destroy(sender: Base, **kwargs):
    if hasattr(sender, '_after_destroy') and (after_destroy := getattr(sender, '_after_destroy', None)):
        after_destroy()
        
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


class Base(ScrapyBase):
    """Base class for all models in the application."""
    __abstract__ = True

    # == Columns =========================================================

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime.datetime] = mapped_column( DateTime(timezone=True), nullable=False, server_default=func.now() )
    updated_at: Mapped[datetime.datetime] = mapped_column( DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now() )
    
    # == Hooks ========================================================================
    
    def _before_save(self): pass
    def _after_save(self): pass
    
    def _before_insert(self): pass
    def _after_insert(self): pass
    
    def _before_update(self): pass
    def _after_update(self): pass
    
    def _before_destroy(self): pass
    def _after_destroy(self): pass
    
    def _before_refresh(self): pass
    def _after_refresh(self): pass
    
    def _before_commit(self): pass
    def _after_commit(self): pass
    
    def _before_flush(self): pass
    def _after_flush(self): pass

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

    # == query helpers ==========================================================================
    
    @classmethod
    def find(cls, id: int) -> Self | None:
        """Find a model instance by its regular id column."""
        with cls.session_context() as session:
            query = select(cls).where(cls.id == id)
            result = session.execute(query).scalar_one_or_none()
            return result if result else None
                       

    # == SYNC Persistence Methods =========================================================
        
    def save(self):
        """Active record dumb save method (sync)."""
        with self.__class__.session_context() as session:
            with send_signal_pair("save", self):
                with send_signal_pair("insert" if self.is_new else "update", self):
                    session.add(self)
                    self.commit()
                    self.flush()
                    self.refresh()

    def destroy(self):
        """Delete this model instance from the database (sync)."""
        with self.__class__.session_context() as session:
            with send_signal_pair("destroy", self):
                session.delete(self)
                self.commit()
                self.flush()

    def commit(self):
        """Commit the current session (sync)."""
        with self.__class__.session_context() as session:
            with send_signal_pair("commit", self):
                session.commit()

    def refresh(self):
        """Refresh the model instance from the database (sync)."""
        with self.__class__.session_context() as session:
            with send_signal_pair("refresh", self):
                session.refresh(self)

    def flush(self):
        """Flush the current session (sync)."""
        with self.__class__.session_context() as session:
            with send_signal_pair("flush", self):
                session.flush()
        
    # == SYNC Session Management Methods =========================================================
    
    @classmethod
    @contextmanager
    def session_context(cls) -> Generator[Session, None, None]:
        """
        Context manager that is the high level unit of operational work spanning multiple AR operations.

        This has an explicit close call that releases the session back to the pool.

        Model usage requires this to be performed at a high level within the application's request/response cycle.

        Usage:

        ```python
        with Model.context() as models:
            CrawlItem.create(
                url="https://example.com",
                title="Example Crawl Item"
            )

            # Perform other operations within the same session
            # no matter how deep in the stack you are, as long
            # as you used this, your models will work.
            def request_handler():
                # This can be any function that needs to use the models
                model = models.CrawlItem.find(1)

            models.CrawlItem.update_all({"title": "Updated Title"}, id=1)
        ```
        """
        session = session_ctx.get(None)
        is_owner = False
        if session is None:
            with cls.session() as session:
                token = session_ctx.set(session)
                owner_token = session_owner_ctx.set(True)
                is_owner = True
                try:
                    yield session
                finally:
                    if is_owner:
                        session_ctx.reset(token)
                        session_owner_ctx.reset(owner_token)
        else:
            # Nesting within an existing session, just yield but don't close it
            yield session
    
    @classmethod
    @contextmanager
    def session(cls) -> Generator[Session, None, None]:
        """
        Context manager that yields a context-local Session.
        Ensures the same session is reused within the same sync context.
        """
        session = settings.db.get_primary_sync().sync_session()
        try:
            yield session
        finally:
            session.close()
        
    
        

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
    def hydrate(cls: type[Self], **kwargs: Any) -> Self:
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
