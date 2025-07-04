from typing import Self

import psycopg2

from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool
from pydantic import BaseModel, Field, field_validator

from pgmcp.data_source_name import DataSourceName


class DatabaseConnectionSettings(BaseModel):
    """A single database connection configuration with a mandatory _name_ and _dsn_."""

    # Required
    name                     : str                  = Field(...,  description="Unique name for this database connection")
    dsn                      : DataSourceName       = Field(...,  description="Data Source Name (DSN) for this database connection")

    # Optional

    encoding                 : str                  = Field(default="utf8",    description="Client encoding")
    timezone                 : str                  = Field(default="UTC", description="IANA timezone name (e.g., 'America/New_York', ISO 8601/ISO 3166)")
    readonly                 : bool                 = Field(default=False,     description="Open connection in read-only mode")

    connection_timeout        : int | None           = Field(default=10,        description="Connection timeout in seconds")
    command_timeout           : int | None           = Field(default=None,      description="Command execution timeout in seconds, None for no timeout")
    


    # Connection pool settings
    pool_min_connections     : int | None           = Field(default=1,         description="Minimum number of connections in the pool")
    pool_max_connections     : int | None           = Field(default=10,        description="Maximum number of connections in the pool")
    pool_max_idle_time       : int | None           = Field(default=300,       description="Maximum idle time for connections in the pool (seconds)")
    pool_max_lifetime        : int | None           = Field(default=3600,      description="Maximum lifetime for connections in the pool (seconds)")
    pool_recycle_time        : int | None           = Field(default=1800,      description="Time after which connections are recycled (seconds)")
    pool_pre_ping            : bool                 = Field(default=True,      description="Enable pre-ping to check connection health")

    keepalives               : bool                 = Field(default=True,      description="Enable TCP keepalives")
    keepalives_idle          : int | None           = Field(default=60,      description="TCP keepalive idle time (seconds)")
    keepalives_interval      : int | None           = Field(default=10,      description="TCP keepalive interval (seconds)")
    keepalives_count         : int | None           = Field(default=5,      description="TCP keepalive probe count")

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
    
    @property
    def username(self) -> str: return self.dsn.username
    
    @property
    def password(self) -> str | None: return self.dsn.password.get_secret_value() if self.dsn.password else None
    
    @property
    def host(self) -> str: return self.dsn.hostname
    
    @property
    def port(self) -> int: return self.dsn.port
    
    @property
    def database(self) -> str: return self.dsn.database if self.dsn.database else ""
    
    @property
    def query(self) -> dict[str, str] | None: return self.dsn.query


    @classmethod
    def from_name_and_dsn(cls, name: str, dsn:str) -> Self:
        """Create a DatabaseConnection instance from a name and DSN string or DataSourceName."""
        return cls.model_validate({
            "name": name,
            "dsn": dsn
        })

    
    # =========================================================================
    # Third-party library factories
    # =========================================================================
    
    
    def create_psycopg2_connection(self):
        """Create a psycopg2 connection using this configuration."""
        
        dsn = self.dsn.model_dump_string(mask_secrets=False)
        
        # Mapping this model's fields to psycopg2's connect parameters
        kwargs = {}
        
        # Connection timeouts
        if self.connection_timeout:
            kwargs['connect_timeout'] = self.connection_timeout
        
        # Server settings via connection string parameters
        # psycopg2 handles most settings via the DSN or connection parameters
        
        return psycopg2.connect(dsn, **kwargs)


    def create_psycopg2_pool(self):
        """Create a psycopg2 threaded connection pool using this configuration."""
        
        dsn = self.dsn.model_dump_string(mask_secrets=False)
        
        # Mapping this model's fields to psycopg2 pool parameters
        minconn = self.pool_min_connections or 1
        maxconn = self.pool_max_connections or 10
        
        # Connection parameters
        kwargs = {}
        if self.connection_timeout:
            kwargs['connect_timeout'] = self.connection_timeout
        
        return ThreadedConnectionPool(minconn, maxconn, dsn, **kwargs)
