# Set up logger to stream to stdout at DEBUG level
import concurrent.futures, logging, os, subprocess, sys, time

from contextlib import contextmanager
from typing import List
from urllib.parse import urlparse

import psycopg2, pytest

from typing_extensions import Generator

from pgmcp.db_ops import DbOps
from pgmcp.settings import get_settings


logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.handlers = [handler]
logger.setLevel(logging.DEBUG)

settings = get_settings()

def get_test_db_dcs():
    return settings.db.get_primary_sync()

def db_ops() -> DbOps:
    return DbOps(get_test_db_dcs())





def truncate_test_db_tables():
    """Truncates all tables in the test database except for alembic_version."""
    start_time = time.perf_counter()
    table_names = db_ops().table_names
    immutable_tables = db_ops().immutable_tables
    applicable_tables = [table for table in table_names if table not in immutable_tables]

    logger.debug(f"Truncating {len(applicable_tables)} tables: {applicable_tables}")

    def truncate(table):
        # Each thread gets its own DbOps instance for thread safety
        # db_ops().truncate_table(table, cascade=True, if_exists=True)
        db_ops().trashy_truncate_table(table, cascade=True, if_exists=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(truncate, applicable_tables))
    
    elapsed = time.perf_counter() - start_time
    logger.info(f"Truncated {len(applicable_tables)} tables in {elapsed:.3f} seconds")
    



# Bootstrapper where all of the other ensure methods converge
# call this from a pytest fixture autouse hook
def setup_database():
    """
    Ensures the test database exists and is migrated.
    - If the DB does not exist, it creates it.
    - If it exists, it runs Alembic migrations.
    """
    logger.info("Ensuring test database is ready for tests")
    truncate_test_db_tables()
    

    logger.info("TEST DATABASE: Setup complete")
