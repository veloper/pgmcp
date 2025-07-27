"""
Simplified Pydantic v2 settings configuration for Multi-Database MCP Server.
Supports .env files, environment variables, and runtime validation with DSN-based configuration.
"""



from pathlib import Path
from typing import Any, Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pgmcp.database_connection_settings import DatabaseConnectionSettings
from pgmcp.environment import Environment


ROOT_PATH = Path(__file__).parent.parent.parent
ENV_FILE_PATH = ROOT_PATH / Environment.get_dotenv_filename()

class AppSettings(BaseSettings):
    """Main application configuration."""

    log_level: str = Field(default="INFO", description="Logging level", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    root_path: Path = Field(default=ROOT_PATH, description="Root path of the application")
    
    @property
    def src_path(self) -> Path: return self.root_path / "src"
    
    @property
    def package_path(self) -> Path: return self.src_path / "pgmcp"
        
        
    
class DbSettings(BaseSettings):

    model_config = SettingsConfigDict( env_nested_delimiter='__')

    connections: Dict[str, DatabaseConnectionSettings]

    def get_primary(self) -> DatabaseConnectionSettings:
        if primary := self.connections.get("primary", None):
            return primary
        raise ValueError("Primary database connection is not defined or is invalid.")
    
    
    def get_primary_sync(self) -> DatabaseConnectionSettings:
        """Get the primary database connection settings for synchronous operations."""
        if primary_sync := self.connections.get("primary_sync", None):
            return primary_sync
        raise ValueError("Primary synchronous database connection is not defined or is invalid.")
    
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
            },
            "primary_sync": {
                "dsn": "postgresql+psycopg://postgres@localhost:5432/postgres",
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
        env_file=(ENV_FILE_PATH), # you are here trying to figure out why this is not as expected even with the singleton of environment being confirmed set to testing
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
    )
            
    app: AppSettings 
    db: DbSettings
    age: AgeSettings
    vectorize: VectorizeSettings
    env: Environment = Field(default_factory=Environment.current, description="Current application environment")
    
    def primary_database(self) -> DatabaseConnectionSettings:
        """Retrieve the primary database connection settings."""
        return self.db.get_primary()
    
class _SettingsTesting(Settings):
    """Settings for testing environment."""
    
    model_config = SettingsConfigDict(
        env_file=(ROOT_PATH / '.env.testing'),
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
    )
    env: Environment = Field(default_factory=lambda: Environment("testing"), description="Current application environment")

class _SettingsDevelopment(Settings):
    """Settings for development environment."""
    
    model_config = SettingsConfigDict(
        env_file=(ROOT_PATH / '.env'),
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
    )
    env: Environment = Field(default_factory=lambda: Environment("development"), description="Current application environment")


# Global settings singleton
SETTINGS: Dict[Environment,Settings] = {}

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
    current_env = Environment.current()
    global SETTINGS
    if SETTINGS.get(current_env, None) is None:
        if current_env.is_production():
            raise ValueError("Production environment is not supported yet.")
        elif current_env.is_staging():
            raise ValueError("Staging environment is not supported yet.")
        elif current_env.is_testing():
            SETTINGS[Environment.TESTING] = _SettingsTesting()  # pyright: ignore
        elif current_env.is_development():
            SETTINGS[Environment.DEVELOPMENT] = _SettingsDevelopment()  # pyright: ignore
        else:
            raise ValueError(f"Unsupported environment: {current_env.value}. Please set the environment to 'testing' or 'development'.")

    settings = SETTINGS.get(current_env, None)
    if settings is None:
        raise ValueError(f"Settings for environment {current_env.value} are not initialized.")

    return settings

