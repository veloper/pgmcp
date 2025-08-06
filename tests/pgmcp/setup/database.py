# Set up logger to stream to stdout at DEBUG level
import logging, sys, time

from pgmcp.db_ops import DbOps
from pgmcp.settings import get_settings


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.handlers = [handler]


def get_test_db_dcs():
    return get_settings().db.get_primary_sync()

def db_ops() -> DbOps:
    return DbOps(get_test_db_dcs())


def truncate_test_db_tables():
    """Truncates all tables in the test database except for alembic_version."""
    start_time = time.perf_counter()
    
    logger.debug(f"Truncating test database tables...")
    
    table_names = db_ops().get_delete_order()
    immutable_tables = db_ops().immutable_tables
    applicable_tables = [table for table in table_names if table not in immutable_tables]
    db_ops().trashy_truncate_tables(applicable_tables)

    elapsed = time.perf_counter() - start_time
    logger.info(f"Truncated {len(applicable_tables)} tables in {elapsed:.3f} seconds")
    



# Bootstrapper where all of the other ensure methods converge
# call this from a pytest fixture autouse hook
def setup_database():
    logger.info("Ensuring test database is ready for tests")
    # truncate_test_db_tables()
    logger.info("TEST DATABASE: Setup complete")
