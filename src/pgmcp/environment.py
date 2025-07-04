import os

from enum import Enum
from typing import Self


OS_ENV_KEY = "APP_ENV" # Environment variable key for application environment

class Environment(Enum):
    
    """Enumeration for application environments."""
    PRODUCTION  = "production"
    STAGING     = "staging"
    DEVELOPMENT = "development"
    TESTING     = "testing"

    @classmethod
    def current(cls) -> Self:
        """Get the current environment from the APP_ENV environment variable."""
        os.environ.setdefault(OS_ENV_KEY, "development")
        app_env = os.environ[OS_ENV_KEY].lower()
        return cls(app_env)

    @classmethod
    def set_current_to(cls, env: str | Self) -> None:
        instance = cls(env) if isinstance(env, str) else env
        if not isinstance(instance, cls):
            raise ValueError(f"Invalid environment: {env}. Must be one of {list(cls)}.")
        os.environ[OS_ENV_KEY] = instance.value
        
    def is_development(self) -> bool: return self == self.__class__.DEVELOPMENT
    def is_staging(self)     -> bool: return self == self.__class__.STAGING
    def is_production(self)  -> bool: return self == self.__class__.PRODUCTION
    def is_testing(self)     -> bool: return self == self.__class__.TESTING
    
    def dotenv_filename(self) -> str:
        """Get the appropriate .env file for the current environment."""
        return self.get_dotenv_filename()

    @classmethod
    def get_dotenv_filename(cls) -> str:
        """Get the appropriate .env filename based on the current environment."""
        if cls.current() == cls.DEVELOPMENT:
            return '.env'
        return f'.env.{cls.current().value}'


def get_current_env() -> Environment: return Environment.current()
def set_current_env(env: str | Environment) -> Environment:
    """Sets the current environment to the specified value and returns it."""
    Environment.set_current_to(env)
    return get_current_env()  
