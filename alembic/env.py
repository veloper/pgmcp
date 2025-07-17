import importlib, pkgutil

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
# add your model's MetaData object here
# for 'autogenerate' support
from pgmcp.models.base import Base
from pgmcp.settings import get_settings


# Force import all model modules so their tables are registered
def import_all_model_modules():
    import pgmcp.models
    for _, module_name, is_pkg in pkgutil.iter_modules(pgmcp.models.__path__):
        if not is_pkg:
            importlib.import_module(f"pgmcp.models.{module_name}")

import_all_model_modules()



pgmcp_settings = get_settings()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Set the target_metadata for Alembic autogenerate
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# FIX: Use the string DSN from the primary connection settings
alembic_dsn = str(pgmcp_settings.db.get_primary().dsn)
if "+asyncpg" in alembic_dsn:
    alembic_dsn = alembic_dsn.replace("+asyncpg", "")
config.set_main_option( "sqlalchemy.url", alembic_dsn )


# List of extension tables to ignore in Alembic autogenerate
EXTENSION_TABLES = {
    'us_lex', 'us_gaz', 'us_rules', 'part_config', 'part_config_sub'
}

def should_include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in EXTENSION_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=should_include_object,
    )

    with context.begin_transaction():
        context.run_migrations()




def run_migrations_online() -> None:
    """Run migrations in 'online' mode with sync SQLAlchemy engine."""
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            include_object=should_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
