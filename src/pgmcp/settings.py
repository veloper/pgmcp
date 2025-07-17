"""
Simplified Pydantic v2 settings configuration for Multi-Database MCP Server.
Supports .env files, environment variables, and runtime validation with DSN-based configuration.
"""



from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List

from pydantic import BaseModel, Field, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from pgmcp.database_connection_settings import DatabaseConnectionSettings
from pgmcp.environment import Environment


ROOT_PATH = Path(__file__).parent.parent.parent
ENV_FILE_PATH = ROOT_PATH / Environment.get_dotenv_filename()

class AppSettings(BaseSettings):
    """Main application configuration."""

    log_level: str = Field(default="INFO", description="Logging level", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
class DbSettings(BaseSettings):

    model_config = SettingsConfigDict( env_nested_delimiter='__')

    connections: Dict[str, DatabaseConnectionSettings]

    def get_primary(self) -> DatabaseConnectionSettings:
        if primary := self.connections.get("primary", None):
            return primary
        raise ValueError("Primary database connection is not defined or is invalid.")
    
    
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

class VectorizeSettings(BaseSettings):
    """Vectorization settings."""
    # GUCs
    batch_size                 : int         = Field(default=10000, description="Batch size for vectorize jobs")
    num_bgw_proc               : int         = Field(default=1, description="Number of background worker processes")
    embedding_req_timeout_sec  : int         = Field(default=120, description="Embedding request timeout in seconds")
    embedding_service_api_key  : str | None  = Field(default=None, description="Embedding service API key")
    embedding_service_host     : str | None  = Field(default=None, description="Embedding service host URL")
    openai_base_url            : str | None  = Field(default="https://api.openai.com/v1", description="OpenAI base URL")
    host                       : str | None  = Field(default=None, description="Postgres unix socket or host")
    database_name              : str | None  = Field(default=None, description="Target database for vectorize operations")
    openai_key                 : str | None  = Field(default=None, description="OpenAI API key")
    ollama_service_host        : str | None  = Field(default=None, description="Ollama service host")
    tembo_service_host         : str | None  = Field(default=None, description="Tembo service host")
    tembo_api_key              : str | None  = Field(default=None, description="Tembo API key (JWT)")
    cohere_api_key             : str | None  = Field(default=None, description="Cohere API key")
    portkey_api_key            : str | None  = Field(default=None, description="Portkey API key")
    portkey_virtual_key        : str | None  = Field(default=None, description="Portkey virtual key")
    portkey_service_url        : str | None  = Field(default=None, description="Portkey service URL")

    # Function Level Settings
    transformer_provider: str | None = Field(default="openai", description="Transformer provider for vectorization")
    transformer_model: str | None = Field(default="text-embedding-ada-002", description="Transformer model name for vectorization")

    @property
    def transformer(self) -> str:
        """Return the transformer provider and model as a single string suitable for the vectorize.table(..., transformer=...) parameter."""
        return f"{self.transformer_provider}/{self.transformer_model}"

    def to_gucs_alter_statements(self) -> List[str]:
        """Convert all settings that are not None to a string of GUC alter system set statements."""
        gucs = []
        for field_name, field_value in VectorizeSettings.model_fields.items():
            value = getattr(self, field_name)
            if value is not None:
                psql_escaped_value = str(value).replace("'", "''")  # Escape single quotes for SQL
                gucs.append(f"ALTER SYSTEM SET vectorize.{field_name} = '{psql_escaped_value}';")
        return gucs


class Settings(BaseSettings):
    """Complete application settings with multi-database support."""
    
    model_config = SettingsConfigDict(
        env_file=(ENV_FILE_PATH),
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
    )
            
    app: AppSettings 
    db: DbSettings
    age: AgeSettings
    vectorize: VectorizeSettings
    
    def primary_database(self) -> DatabaseConnectionSettings:
        """Retrieve the primary database connection settings."""
        return self.db.get_primary()
    
    

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

