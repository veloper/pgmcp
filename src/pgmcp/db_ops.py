from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import psycopg2

from pgmcp.settings import DatabaseConnectionSettings


class DbOps:
    
    REQUIRED_EXTENSIONS = [
        "plpgsql",
        "vector",
        "age",
        "http",
        "plpython3u",
        "hstore",
        "ltree",
        "fuzzystrmatch",
        "bloom",
        "uuid-ossp",
        "xml2",
        "autoinc",
        "address_standardizer_data_us",
        "citext",
        "pg_similarity",
        "pljs",
        "pg_trgm",
        "pgmq",
        "unaccent",
        "pgcrypto"
    ]
    
    REQUIRED_SCHEMAS = [
        "ag_catalog",
        "pg_catalog",
        "information_schema",
        "public",
        "cron",
        "pgmq"
    ]
    
    IMMUTABLE_TABLES = [
        "alembic_version",
        "pg_stat_statements",
        "us_gaz",
        "us_lex",
        "us_rules"
    ]
    
    def __init__(self, dcs: DatabaseConnectionSettings):
        self._dcs = dcs
        self._active_database = dcs.database # change this to change how the admin connects.
        

    # ===========================================
    # Properties
    # ===========================================
    
    def set_active_database(self, database: str) -> None:
        self._active_database = database
        
    def get_active_database(self) -> str:
        return self._active_database
    
    def reset_active_database(self) -> None:
        self._active_database = self._dcs.database
    
    
    def get_dcs(self) -> DatabaseConnectionSettings:
        """Return a copy of the DatabaseConnectionSettings for flexibility, always recreated on call"""
        dcs = self._dcs.deepcopy()
        dcs.database = self.get_active_database()
        return dcs

    @property
    def required_extensions(self) -> List[str]: return self.REQUIRED_EXTENSIONS

    @property
    def immutable_tables(self) -> List[str]: return self.IMMUTABLE_TABLES
    
    @property
    def required_schemas(self) -> List[str]: return self.REQUIRED_SCHEMAS

            
    
    # ===========================================
    # Psycopg2 Context Managers
    # ===========================================
    

    @contextmanager
    def connection(self, *, db : str | None = None) -> Generator[psycopg2.extensions.connection, None, None]:
        original_db = self.get_active_database()
        if db:
            self.set_active_database(db)
        dcs = self.get_dcs()
        conn = psycopg2.connect( dbname=dcs.database, user=dcs.username, password=dcs.password, host=dcs.host, port=dcs.port )
        try:
            conn.autocommit = True  # Ensure autocommit is set for test DB operations
            yield conn
        finally:
            conn.close()
            self.set_active_database(original_db)

    @contextmanager
    def cursor(self, *, db: str | None = None) -> Generator[psycopg2.extensions.cursor, None, None]:
        with self.connection(db=db) as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    # ===========================================
    # Role/User Management
    # ===========================================
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists in the database."""
        with self.cursor(db="postgres") as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (username,))
            return cur.fetchone() is not None

    def user_is_superuser(self, username: str) -> bool:
        """Check if a user is a superuser."""
        with self.cursor(db="postgres") as cur:
            cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = %s", (username,))
            row = cur.fetchone()
            return row[0] if row is not None else False

    def user_is_owner_of_db(self, username: str, database: str) -> bool:
        """Check if a user is the owner of a specific database."""
        with self.cursor(db="postgres") as cur:
            cur.execute("SELECT datdba = (SELECT oid FROM pg_roles WHERE rolname = %s) FROM pg_database WHERE datname = %s", (username, database))
            row = cur.fetchone()
            return row[0] if row is not None else False

    def user_has_access_to_schema(self, username: str, schema: str) -> bool:
        """Check if a user has access to a specific schema."""
        with self.cursor() as cur:
            try:
                cur.execute("SELECT has_schema_privilege(%s, %s, 'USAGE')", (username, schema))
                row = cur.fetchone()
                return row[0] if row is not None else False
            except psycopg2.Error:
                return False
    
    def create_user(self, username: str, password: Optional[str] = None, superuser: bool = False) -> None:
        """Create a new database user."""
        with self.cursor(db="postgres") as cur:
            stmt = f"CREATE USER {username}"
            if password:
                stmt += f" WITH PASSWORD %s"
                if superuser:
                    stmt += " SUPERUSER"
                cur.execute(stmt, (password,))
            else:
                if superuser:
                    stmt += " WITH SUPERUSER"
                cur.execute(stmt)

    def drop_user(self, username: str, if_exists: bool = True) -> None:
        """Drop a database user."""
        with self.cursor(db="postgres") as cur:
            stmt = f"DROP USER {'IF EXISTS ' if if_exists else ''}{username}"
            cur.execute(stmt)

    def alter_user(self, username: str, **options) -> None:
        """Alter user options (e.g., password, superuser)."""
        with self.cursor(db="postgres") as cur:
            opts = []
            if 'password' in options:
                opts.append(f"PASSWORD '{options['password']}'")
            if options.get('superuser'):
                opts.append("SUPERUSER")
            if options.get('nosuperuser'):
                opts.append("NOSUPERUSER")
            if not opts:
                return
            stmt = f"ALTER USER {username} {' '.join(opts)}"
            cur.execute(stmt)

    def grant_role(self, role: str, to_user: str) -> None:
        """Grant a role to a user."""
        with self.cursor(db="postgres") as cur:
            stmt = f"GRANT {role} TO {to_user}"
            cur.execute(stmt)

    def revoke_role(self, role: str, from_user: str) -> None:
        """Revoke a role from a user."""
        with self.cursor(db="postgres") as cur:
            stmt = f"REVOKE {role} FROM {from_user}"
            cur.execute(stmt)

    # ===========================================
    # Schema Management
    # ===========================================

    def create_schema(self, schema: str, if_not_exists: bool = True) -> None:
        """Create a schema."""
        with self.cursor() as cur:
            stmt = f"CREATE SCHEMA {'IF NOT EXISTS ' if if_not_exists else ''}{schema}"
            cur.execute(stmt)

    def drop_schema(self, schema: str, if_exists: bool = True, cascade: bool = False) -> None:
        """Drop a schema."""
        with self.cursor() as cur:
            stmt = f"DROP SCHEMA {'IF EXISTS ' if if_exists else ''}{schema}{' CASCADE' if cascade else ''}"
            cur.execute(stmt)

    def grant_schema_privilege(self, privilege: str, schema: str, to_user: str) -> None:
        """Grant a privilege on a schema to a user."""
        with self.cursor() as cur:
            stmt = f"GRANT {privilege} ON SCHEMA {schema} TO {to_user}"
            cur.execute(stmt)

    def revoke_schema_privilege(self, privilege: str, schema: str, from_user: str) -> None:
        """Revoke a privilege on a schema from a user."""
        with self.cursor() as cur:
            stmt = f"REVOKE {privilege} ON SCHEMA {schema} FROM {from_user}"
            cur.execute(stmt)
    
    @property
    def schema_names(self) -> List[str]:
        """Get the names of all schemas in the current database."""
        with self.cursor() as cur:
            cur.execute("""SELECT nspname FROM pg_namespace ORDER BY nspname""")
            return [row[0] for row in cur.fetchall()]

    # ===========================================
    # Table Management
    # ===========================================


    @property
    def table_names(self) -> List[str]:
        """Get the table names for the current database."""
        with self.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            return [row[0] for row in cur.fetchall()]        

    def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """Drop the specified table, optionally if it exists."""
        with self.cursor() as cur:
            stmt = f"DROP TABLE {'IF EXISTS ' if if_exists else ''}{table_name}"
            cur.execute(stmt)


    def create_table(self, table_name: str, columns_sql: str, if_not_exists: bool = True, schema: str | None = None) -> None:
        """Create a table with the given name and columns definition. Optionally skip if exists."""
        with self.cursor() as cur:
            full_table = f"{schema}.{table_name}" if schema else table_name
            stmt = f"CREATE TABLE {'IF NOT EXISTS ' if if_not_exists else ''}{full_table} ({columns_sql})"
            cur.execute(stmt)


    def rename_table(self, old_name: str, new_name: str, schema: Optional[str] = None) -> None:
        """Rename a table."""
        with self.cursor() as cur:
            full_old = f"{schema}.{old_name}" if schema else old_name
            stmt = f"ALTER TABLE {full_old} RENAME TO {new_name}"
            cur.execute(stmt)

    def alter_table(self, table_name: str, alteration: str, schema: Optional[str] = None) -> None:
        """Alter a table with a given alteration clause (e.g., ADD COLUMN ...)."""
        with self.cursor() as cur:
            full_table = f"{schema}.{table_name}" if schema else table_name
            stmt = f"ALTER TABLE {full_table} {alteration}"
            cur.execute(stmt)

    def truncate_table(self, table_name: str, cascade: bool = False, if_exists: bool = False) -> None:
        """Truncate a table. If if_exists is True, only truncate if the table exists (checked in a transaction)."""
        with self.connection() as conn:
            with conn.cursor() as cur:
                # Explicitly start a transaction block
                cur.execute("BEGIN")
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                """, (table_name,))
                result = cur.fetchone()
                exists = result[0] if result else False
                if not exists and if_exists:
                    cur.execute("ROLLBACK")
                    return
                stmt = f"TRUNCATE TABLE {table_name}{' CASCADE' if cascade else ''}"
                cur.execute(stmt)
                cur.execute("COMMIT")
        
    def trashy_truncate_table(self, table_name: str, cascade: bool = False, if_exists: bool = False) -> None:
        """Truncate a table without using TRUNCATE, instead using DELETE where 1=1."""
        with self.connection() as conn:
            with conn.cursor() as cur:
                # Explicitly start a transaction block
                cur.execute("BEGIN")
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                """, (table_name,))
                result = cur.fetchone()
                exists = result[0] if result else False
                if not exists and if_exists:
                    cur.execute("ROLLBACK")
                    return
                stmt = f"DELETE FROM {table_name} WHERE 1=1"
                cur.execute(stmt)
                if cascade:
                    # Handle cascading deletes manually if needed
                    pass
                cur.execute("COMMIT")

    def copy_table_structure(self, source_table: str, target_table: str, schema: Optional[str] = None, if_not_exists: bool = True) -> None:
        """Copy table structure (CREATE TABLE ... LIKE ...)."""
        with self.cursor() as cur:
            full_source = f"{schema}.{source_table}" if schema else source_table
            full_target = f"{schema}.{target_table}" if schema else target_table
            stmt = f"CREATE TABLE {'IF NOT EXISTS ' if if_not_exists else ''}{full_target} (LIKE {full_source} INCLUDING ALL)"
            cur.execute(stmt)

    def table_exists(self, table_name: str, schema: str = 'public') -> bool:
        """Check if a table exists in a schema."""
        with self.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                )
            """, (schema, table_name))
            row = cur.fetchone()
            return row[0] if row else False

    # ===========================================
    # Database Health/Connection/Control
    # ===========================================

    def create_database(self, name: str, owner: str, if_not_exists: bool = True) -> None:
        """Create a new database with the given name and owner. Optionally skip if it exists."""
        with self.cursor(db="postgres") as cur:
            if if_not_exists:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
                if cur.fetchone():
                    return
            cur.execute(f"CREATE DATABASE {name} OWNER {owner}")

    def drop_database(self, name: str) -> None:
        """Drop the specified database."""
        with self.cursor(db="postgres") as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {name}")

    def ping(self) -> bool:
        """Check if the database connection is alive."""
        try:
            with self.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                return row is not None and row[0] == 1
        except Exception:
            return False

    def get_server_version(self) -> Optional[str]:
        """Get the PostgreSQL server version."""
        with self.cursor() as cur:
            cur.execute("SHOW server_version")
            row = cur.fetchone()
            return row[0] if row else None

    
    
    # ===========================================
    # Extension Management
    # ===========================================

    def drop_extension(self, name: str, if_exists: bool = True, cascade: bool = False) -> None:
        """Drop a PostgreSQL extension."""
        with self.cursor() as cur:
            stmt = f"DROP EXTENSION {'IF EXISTS ' if if_exists else ''}{name}{' CASCADE' if cascade else ''}"
            cur.execute(stmt)

    @property
    def installed_extensions(self) -> List[str]:
        """List extensions installed in a specific database."""
        with self.cursor() as cur:
            cur.execute("SELECT extname FROM pg_extension")
            return [row[0] for row in cur.fetchall()]

    @property
    def available_extensions(self) -> List[str]:
        """List available extensions that _can_ or _are_ installed."""
        with self.cursor() as cur:
            cur.execute("SELECT name FROM pg_available_extensions")
            return [row[0] for row in cur.fetchall()]

    def create_extension(self, name: str, *, if_not_exists: bool = True) -> None:
        """Create a PostgreSQL extension, optionally in a specific schema, with IF NOT EXISTS support."""
        with self.cursor() as cur:
            stmt = f"CREATE EXTENSION {'IF NOT EXISTS ' if if_not_exists else ''}\"{name}\""
            cur.execute(stmt)



    # ===========================================
    # Misc
    # ===========================================

    @property
    def database_names(self) -> list:
        """List all databases."""
        with self.cursor(db="postgres") as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
            return [row[0] for row in cur.fetchall()]

    @property
    def role_names(self) -> list:
        """List all roles."""
        with self.cursor(db="postgres") as cur:
            cur.execute("SELECT rolname FROM pg_roles")
            return [row[0] for row in cur.fetchall()]
