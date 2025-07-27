
from pgmcp.settings import get_settings


settings = get_settings()
dbs = settings.db.get_primary()

async def close_sqlalchemy_engine() -> None:
    """Ensure that the SQLAlchemy engine is disposed of after each test function.
    
    If this is not setup then the SQLAlchemy engine will create more and more unclosed
    connections to the database, leading to resource exhaustion and test failures.

    Again: This should run after each test function.
    """
    await dbs.sqlalchemy_dispose_async_engine()

