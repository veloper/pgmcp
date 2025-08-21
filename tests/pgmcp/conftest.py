
import pytest_asyncio

from pgmcp.environment import Environment, set_current_env
from pgmcp.settings import get_settings

from .setup.database import setup_database


# ===========================================================================================
# ENV AND SETTINGS
# ===========================================================================================

ENV = set_current_env(Environment.TESTING)
SETTINGS = get_settings()
DCS = SETTINGS.db.get_primary()


# ===========================================================================================
# HOOKS
# ===========================================================================================
setup_database()

# Function: Around: Async
@pytest_asyncio.fixture(autouse=True, scope="function")
async def around_function_async():
    """Ensure that the SQLAlchemy engine is disposed of after each test function.
    
    If this is not setup then the SQLAlchemy engine will create more and more unclosed
    connections to the database, leading to resource exhaustion and test failures.

    Again: This should run after each test function.
    """
    
    yield # execution of the test function

    await DCS.sqlalchemy_dispose_async_engine()

    


# ===========================================================================================
# FIXTURES
# ===========================================================================================
