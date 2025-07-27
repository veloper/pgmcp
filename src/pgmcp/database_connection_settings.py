import functools

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, AsyncGenerator, Dict, Self, cast

from pydantic import BaseModel, Field, PrivateAttr, field_validator
from pydantic.types import SecretStr
from sqlalchemy.engine import Engine, Result, create_engine
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import text
from typing_extensions import Literal

from pgmcp.data_source_name import DataSourceName


_sync_session_ctx: ContextVar[Session | None] = ContextVar("_sync_session_ctx", default=None)
_async_session_ctx: ContextVar[AsyncSession | None] = ContextVar("_async_session_ctx", default=None)


class DatabaseConnectionSettings(BaseModel):
    """A single database connection configuration with a mandatory _name_ and _dsn_."""

    # Required
    name                     : str                  = Field(...,  description="Unique name for this database connection")
    dsn                      : DataSourceName       = Field(...,  description="Data Source Name (DSN) for this database connection")


    # Optional
    echo                     : bool                 = Field(default=False,     description="Enable SQL statement logging")
    encoding                 : str                  = Field(default="utf8",    description="Client encoding")
    timezone                 : str                  = Field(default="UTC", description="IANA timezone name (e.g., 'America/New_York', ISO 8601/ISO 3166)")
    readonly                 : bool                 = Field(default=False,     description="Open connection in read-only mode")

    connection_timeout        : int | None           = Field(default=10,        description="Connection timeout in seconds")
    command_timeout           : int | None           = Field(default=None,      description="Command execution timeout in seconds, None for no timeout")
    


    # Connection pool settings
    pool_min_connections     : int | None           = Field(default=5,         description="Minimum number of connections in the pool")
    pool_max_connections     : int | None           = Field(default=10,        description="Maximum number of connections in the pool")
    pool_max_idle_time       : int | None           = Field(default=300,       description="Maximum idle time for connections in the pool (seconds)")
    pool_max_lifetime        : int | None           = Field(default=3600,      description="Maximum lifetime for connections in the pool (seconds)")
    pool_recycle_time        : int | None           = Field(default=1800,      description="Time after which connections are recycled (seconds)")
    pool_pre_ping            : bool                 = Field(default=True,      description="Enable pre-ping to check connection health")
    pool_max_overflow        : int | None           = Field(default=10,      description="Number of connections that can be created beyond the pool size limit")

    keepalives               : bool                 = Field(default=True,      description="Enable TCP keepalives")
    keepalives_idle          : int | None           = Field(default=60,      description="TCP keepalive idle time (seconds)")
    keepalives_interval      : int | None           = Field(default=10,      description="TCP keepalive interval (seconds)")
    keepalives_count         : int | None           = Field(default=5,      description="TCP keepalive probe count")


    _sqlalchemy_async_engine: AsyncEngine | None = PrivateAttr(default=None)
    _sqlalchemy_sync_engine: Engine | None = PrivateAttr(default=None)

    @field_validator('dsn', mode='before')
    @classmethod
    def validate_dsn(cls, v: DataSourceName | str) -> DataSourceName:
        """Ensure DSN is a valid DataSourceName instance."""
        if isinstance(v, str):
            v = DataSourceName.parse(v)

        if not isinstance(v, DataSourceName):
            raise ValueError("dsn must be a valid DataSourceName instance or a string that can be parsed into one.")

        return v

    
    @property
    def driver(self) -> str: return self.dsn.driver
    
    @driver.setter
    def driver(self, value: str) -> None: self.dsn.driver = value
    
    @property
    def username(self) -> str: return self.dsn.username
    
    @username.setter
    def username(self, value: str) -> None: self.dsn.username = value
    
    
    @property
    def password(self) -> str | None: return self.dsn.password.get_secret_value() if self.dsn.password else None
    
    @password.setter
    def password(self, value: str | None) -> None: self.dsn.password = SecretStr(value) if value else None

    @property
    def host(self) -> str: return self.dsn.hostname
    
    
    @host.setter
    def host(self, value: str) -> None: self.dsn.hostname = value

    @property
    def port(self) -> int: return self.dsn.port
    @port.setter
    def port(self, value: int) -> None: self.dsn.port = value
    
    @property
    def database(self) -> str: return self.dsn.database if self.dsn.database else ""
    @database.setter
    def database(self, value: str) -> None: self.dsn.database = value

    @property
    def query(self) -> dict[str, str] | None: return self.dsn.query
    
    # if you need query, implement it then.
    


    def deepcopy(self) -> Self:
        """Return a deep copy of this DatabaseConnectionSettings instance."""
        return self.model_copy(deep=True)

    @classmethod
    def from_name_and_dsn(cls, name: str, dsn:str) -> Self:
        """Create a DatabaseConnection instance from a name and DSN string or DataSourceName."""
        return cls.model_validate({
            "name": name,
            "dsn": dsn
        })

    @classmethod
    def from_name_and_connection_object(cls, name: str, connection_obj: Dict[str, Any]) -> Self:
        """Create a DatabaseConnection instance from a name and connection object from the .env file."""
        return cls.model_validate({
            "name": name,
            **connection_obj
        })



    # ==================================================================================================
    # SQLAlchemy Sync 
    # - These methods may only be used with a connection that uses psycopg2 or similar synchronous driver
    # ==================================================================================================
    
    def sync_engine(self) -> Engine:
        """Get or create the SQLAlchemy sync engine for this connection."""
        if not self._sqlalchemy_sync_engine:
            # Map user settings to valid SQLAlchemy engine kwargs
            engine_kwargs = {
                "echo": self.echo,
                "pool_size": self.pool_min_connections, 
                "max_overflow": self.pool_max_overflow, 
                "pool_timeout": self.connection_timeout,
                "pool_recycle": self.pool_recycle_time,
                "pool_pre_ping": self.pool_pre_ping,
                "pool_use_lifo": False,  # FIFO by default, could be exposed if needed
                "future": True
            }

            # Remove None values so SQLAlchemy defaults are used
            engine_kwargs = {k: v for k, v in engine_kwargs.items() if v is not None}

            self._sqlalchemy_sync_engine = create_engine(str(self.dsn), **engine_kwargs)
            
        return self._sqlalchemy_sync_engine
    
    def sync_sessionmaker(self) -> sessionmaker[Session]:
        """Create a sessionmaker CLASS for synchronous sessions."""
        engine = self.sync_engine()
        SessionLocal = sessionmaker(
            bind=engine,
            expire_on_commit=False,
            class_=Session,
            autoflush=False,
            autocommit=False,
        )
        return SessionLocal

    def sync_session(self) -> Session:
        """Create a new SQLAlchemy sync session."""
        if _sync_session_ctx.get() is None:
            # If no session is set in context, create a new one
            klass = self.sync_sessionmaker()
            instance = klass()
            _sync_session_ctx.set(instance)

        if (instance := _sync_session_ctx.get()) and isinstance(instance, Session):
            return cast(Session, instance)
            
        # Should not happen, but just in case
        raise RuntimeError("This exception should not happen, that fact that it does indicates a deeper bug.")
    
    @contextmanager
    def sqlalchemy_sync_transaction(
        self,
        isolation_level: str | None = None
    ):
        """
        Context manager for a SQLAlchemy sync transaction.

        Args:
            isolation_level: Optional transaction isolation level.

        Yields:
            Connection with an active transaction (committed or rolled back on exit).
        """
        engine = self.sync_engine()
        with engine.connect() as conn:
            if isolation_level is not None:
                conn = conn.execution_options(isolation_level=isolation_level)
            with conn.begin():
                yield conn

    
    # ==================================================================================================
    # Async SQLAlchemy Below this point
    # - These methods may only be used with a connection that uses asyncpg
    # ==================================================================================================


    async def sqlalchemy_dispose_async_engine(self) -> None:
        """Dispose the SQLAlchemy async engine if it exists."""
        if self._sqlalchemy_async_engine and isinstance(self._sqlalchemy_async_engine, AsyncEngine):
            await self._sqlalchemy_async_engine.dispose()
            self._sqlalchemy_async_engine = None
    
    async def sqlalchemy_async_engine(self) -> AsyncEngine:
        """Get or create the SQLAlchemy async engine for this connection."""
        if not self._sqlalchemy_async_engine:
            
            # Map user settings to valid SQLAlchemy async engine kwargs
            engine_kwargs = {
                "echo": self.echo,
                # "encoding": self.encoding,  # Removed: asyncpg does not support this argument
                "pool_size": self.pool_min_connections, 
                "max_overflow": self.pool_max_overflow, 
                "pool_timeout": self.connection_timeout,
                "pool_recycle": self.pool_recycle_time,
                "pool_pre_ping": self.pool_pre_ping,
                "pool_use_lifo": False,  # FIFO by default, could be exposed if needed
                "future": True
            }

            # Remove None values so SQLAlchemy defaults are used
            engine_kwargs = {k: v for k, v in engine_kwargs.items() if v is not None}

            self._sqlalchemy_async_engine = create_async_engine( str(self.dsn), **engine_kwargs )

        return self._sqlalchemy_async_engine


    
    async def sqlalchemy_async_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Create a sessionmaker CLASS that is to be instantiated for each session."""
        async_engine = await self.sqlalchemy_async_engine()
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            expire_on_commit=False,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
        )

        return AsyncSessionLocal

    async def sqlalchemy_async_session(self) -> AsyncSession:
        """Create a new SQLAlchemy async session.
        
        Why are we using a ContextVar?
            a: To allow the session to be used in async contexts without leaking across requests.
            b: To allow the session to be used in threads without sharing the same session across threads.
            c: To ensure we use the same session regardless from where we call this function during runtime.
            
        Downsides to this approach:
            - Per request there need to be manual closing of the session so a new one can be created for the next request.
            - If the session is not closed, it will leak and cause issues with connection pool exhaustion
        
        How we mitigate the downsides:
            - We provide a decorator that automatically manages the session lifecycle in request handlers.
            - The decorator ensures that the session is created before the handler runs, and closed after it
              completes, preventing leaks.
            - The decorator also ensures that calls to self.sqlalchemy_async_session() within the handler will
              return the same session, allowing for consistent session usage.
        
        """
        if _async_session_ctx.get() is None:
            # If no session is set in context, create a new one
            klass = await self.sqlalchemy_async_sessionmaker()
            instance = klass()
            _async_session_ctx.set(instance)

        if (instance := _async_session_ctx.get()) and isinstance(instance, AsyncSession):
            return cast(AsyncSession, instance)
            
        # Should not happen, but just in case
        raise RuntimeError("This exception should not happen, that fact that it does indicates a deeper bug.")

    async def sqlalchemy_async_session_close(self) -> None:
        """Close the current SQLAlchemy async session, releasing it back to the pool."""
        if (instance := _async_session_ctx.get()) and isinstance(instance, AsyncSession):
            await instance.close()
            _async_session_ctx.set(None)
         
    def sqlalchemy_async_session_decorator(self):
        """
        Decorator to automatically manage SQLAlchemy async session lifecycle in request handlers.

        This decorator ensures:
            - A session is created before the handler runs.
            - Calls to self.sqlalchemy_async_session() within the handler will return the same session.
            - The session is closed after the handler completes.
            - No auto-commit occurs; the active record pattern expects multiple flushes and commits per request.
        
        
        Usage:
            @db_connection.sqlalchemy_async_session_decorator()
            async def handler(request):
                # Use the session here
                pass

        Returns:
            Callable: An async decorator that injects a managed SQLAlchemy session into the handler.
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                await self.sqlalchemy_async_session()
                try:
                    return await func(*args, **kwargs)
                finally:
                    await self.sqlalchemy_async_session_close()
            return wrapper
        return decorator
        


    

    @asynccontextmanager
    async def sqlalchemy_transaction(
        self, 
        isolation_level: Literal["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"] | None = None
    ) -> AsyncGenerator[AsyncConnection, None]:
        """
        Async context manager for a SQLAlchemy async transaction.

        Args:
            isolation_level: Optional transaction isolation level.

        Yields:
            AsyncConnection with an active transaction (committed or rolled back on exit).
        """
        engine = await self.sqlalchemy_async_engine()
        async with engine.connect() as conn:
            if isolation_level is not None:
                await conn.execution_options(isolation_level=isolation_level)
            async with conn.begin():
                yield conn

    
    async def fetch(
        self, 
        query: str, 
        params: Dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a SELECT query and return all rows as a list of dictionaries.

        Args:
            query: The SQL query string with :param placeholders.
            params: Optional dictionary of parameters.

        Returns:
            List of rows as dictionaries.
        """
        engine = await self.sqlalchemy_async_engine()
        async with engine.connect() as conn:
            result: Result = await conn.execute(text(query), params or {})
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def execute(
        self, 
        query: str, 
        params: Dict[str, Any] | None = None
    ) -> bool:
        """
        Execute a non-SELECT query (INSERT, UPDATE, DELETE).

        Args:
            query: The SQL query string with :param placeholders.
            params: Optional dictionary of parameters.

        Returns:
            True if the statement executed without error.
        """
        engine = await self.sqlalchemy_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text(query), params or {})
            await conn.commit()
            return True
