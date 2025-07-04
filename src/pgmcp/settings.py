"""
Simplified Pydantic v2 settings configuration for Multi-Database MCP Server.
Supports .env files, environment variables, and runtime validation with DSN-based configuration.
"""



from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, AsyncGenerator, Dict

import asyncpg

from pydantic import Field, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pgmcp.database_connection_settings import DatabaseConnectionSettings
from pgmcp.environment import Environment


class AppSettings(BaseSettings):
    """Main application configuration."""

    log_level: str = Field(default="INFO", description="Logging level", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    
class DbSettings(BaseSettings):

    model_config = SettingsConfigDict( env_nested_delimiter='__')

    connections: Dict[str, DatabaseConnectionSettings]

    # Idiomatic Pydantic private attributes
    _pool: asyncpg.Pool | None = PrivateAttr(default=None)
    _connection_ctx: ContextVar[asyncpg.Connection | None] = PrivateAttr(default_factory=lambda: ContextVar("_connection_ctx", default=None))

    def primary_database(self) -> DatabaseConnectionSettings:
        if primary := self.connections.get("primary", None):
            return primary
        raise ValueError("Primary database connection is not defined or is invalid.")
    
    @property
    async def pool(self) -> asyncpg.Pool:
        if not self.primary_database():
            raise ValueError("Primary database connection is not defined or is invalid.")

        if self._pool is None:
            # Create a connection pool for the primary database connection
            primary: DatabaseConnectionSettings = self.primary_database()
            
            async def setup_connection(conn):
                await conn.execute("LOAD 'age';")
                await conn.execute("SET search_path = ag_catalog, '$user', public;")

            self._pool = await asyncpg.create_pool(
                dsn=str(primary.dsn),
                min_size=primary.pool_min_connections or 1,
                max_size= primary.pool_max_connections or 10,
                timeout=primary.connection_timeout or 60,  # Default timeout of 60 seconds
                command_timeout=primary.connection_timeout or 60,  # Default command timeout of 60 seconds
                max_inactive_connection_lifetime=primary.pool_max_idle_time or 300,  # Default max idle time of 5 minutes
                setup=setup_connection,  # Initialize connections with AGE and search_path
            )
            
        return self._pool
    

    async def close_pool(self):
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    
    async def acquire_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool."""
        if pool := await self.pool:
            if conn := await pool.acquire():
                return conn
            raise RuntimeError("Failed to acquire a connection from the pool.")
        raise ValueError("Database connection pool is not initialized.")
    
    async def release_connection(self, conn: asyncpg.Connection) -> None:
        """Release a connection back to the pool."""
        if pool := await self.pool:
            await pool.release(conn)
        else:
            raise ValueError("Database connection pool is not initialized.")

    
    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Reentrant async context manager for acquiring a database connection.
        If already inside a connection context, reuses the same connection.
        
        Usage:
        
        async with db_settings.connection() as conn:
            # Use the connection here
            await conn.execute("SELECT 1")
        
        
        """
        conn = self._connection_ctx.get()
        if conn is not None:
            # Already inside a connection context, yield the same connection
            
            yield conn
            return

        conn = await self.acquire_connection()
        token = self._connection_ctx.set(conn)
        try:
            yield conn
        finally:
            self._connection_ctx.reset(token)
            await self.release_connection(conn)

    # Remove explicit close method; add lazy pool recreation in pool property
    @field_validator('connections', mode='before')
    @classmethod
    def validate_connections(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, DatabaseConnectionSettings]:
        """
        We're getting this...
        
        DB__CONNECTIONS='{
            "primary": {
                "dsn": "postgresql://postgres@localhost:5432/postgres",
                "echo": true
            }
        }'
        
        and we need to coerce this into `primary: DatabaseConnectionSettings(...)`
        """
        # at this point its already a dict, so we can just convert it
        connections = {}
        for name, conn_data in v.items():
            db_name = name
            if isinstance(conn_data, dict) and 'dsn' in conn_data and isinstance(conn_data['dsn'], str):
                if (db_dsn := conn_data.get('dsn')):
                    connections[db_name] = DatabaseConnectionSettings.from_name_and_dsn(db_name, db_dsn)

        if "primary" not in connections:
            raise ValueError("Primary database connection must be defined with the name 'primary'.")

        return connections
        

class AgeSettings(BaseSettings):
    """AGE-specific configuration."""
    ident_property: str
    start_ident_property: str
    end_ident_property: str


class Settings(BaseSettings):
    """Complete application settings with multi-database support."""
    
    model_config = SettingsConfigDict(
        env_file=(Environment.get_dotenv_filename()),
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
    )
            
    app: AppSettings 
    db: DbSettings
    age: AgeSettings
    
    def primary_database(self) -> DatabaseConnectionSettings:
        """Retrieve the primary database connection settings."""
        return self.db.primary_database()
    
    

# Global settings singleton
SETTINGS: Settings | None = None

def get_settings() -> Settings:
    """Retrieve the global settings singleton with lazy environment configuration.
    
    Implements a singleton pattern that configures Pydantic settings based on the current
    environment when first accessed. The environment file and nested delimiter configuration
    are applied dynamically, allowing runtime environment changes before first access.
    
    Returns:
        Settings: The configured global settings instance
        
    Example:
        >>> # Basic usage:
        >>> settings = get_settings()
        >>> db_config = settings.primary_database()
        ...
        >>> # With environment override:
        >>> from pgmcp.environment import set_current_env
        >>> set_current_env('testing')
        >>> settings = get_settings()  # Uses .env.testing file
        
    Note:
        Environment must be set before first call to take effect. Subsequent calls
        return the cached instance regardless of environment changes.
    """
    global SETTINGS
    if SETTINGS is None:
        # Configure Pydantic settings based on current runtime environment
        # Settings.model_config = SettingsConfigDict(
        #     env_file=Environment.get_dotenv_filename(),
        #     env_file_encoding='utf-8',
        #     env_nested_delimiter='__',
        # )
        SETTINGS = Settings()  # pyright: ignore
        
    return SETTINGS

