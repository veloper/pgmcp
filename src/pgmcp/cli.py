import os

from contextlib import contextmanager
from functools import cached_property
from typing import ClassVar, Dict, Generator, List, Tuple

import click, psycopg2

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.traceback import install as install_traceback
from sqlalchemy.engine.cursor import ResultFetchStrategy

from pgmcp.db_ops import DbOps
from pgmcp.environment import set_current_env


console = Console()
install_traceback(show_locals=True, word_wrap=True, console=console)


class Context:
    def __init__(self):
        pass

    def settings(self):
        """Return the settings for the current context."""
        from pgmcp.settings import get_settings
        return get_settings()
    
        

    @cached_property
    def db(self) -> DbOps:
        """Return a DbOps instance for the current context."""
        dcs = self.settings().db.get_primary_sync()
        return DbOps(dcs)



@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """pgmcp: PostgreSQL Model Context Protocol Server CLI."""
    ctx.obj = Context()


@cli.group()
@click.pass_obj
def db(ctx: Context) -> None:
    pass

@db.command()
@click.option('--env', type=click.Choice(['development', 'testing', 'staging', 'production']), default='development', help='Environment to use.')
@click.pass_obj
def migrate(ctx: Context, env: str) -> None:
    """Run database migrations."""
    set_current_env(env)
    settings = ctx.settings()
    
    cmd = settings.app.root_path / ".venv" / "bin" / "alembic"
    cmd_args = ["upgrade", "head"]
    console.log(f"Running migrations with command: {cmd} {' '.join(cmd_args)}")
    console.log(f"Note: If you'd like to run migration against model changes make sure to use `alembic revision --autogenerate -m 'your message'` to create a new migration file.")
    # run alembic by replacing this process via exec
    os.execvp(str(cmd), [str(cmd)] + cmd_args)


@db.command()
@click.option('--env', type=click.Choice(['development', 'testing', 'staging', 'production']), default='development', help='Environment to use.')
@click.option('--fix', is_flag=True, help='Attempt to fix any issues found.')
@click.pass_obj
def doctor(ctx: Context, env: str, fix: bool) -> None:
    """Check the database for potential issues. Attempt to fix issues if --fix is used."""
    set_current_env(env)
    db = ctx.db

    class PotentialIssue:
        ICONS : ClassVar[Dict[str, str]] = {
            "ok": "✅",
            "error": "❌",
            "resolvable": "🔧", # attempting to fix, leading to ok or error.
            "right_arrow": "→"
        }

        name: ClassVar[str | None] = None # None means derive name from self.__class__.__name__

        def __init__(self, autofix: bool = False):
            self.notes = []
            self.status = ""
            self.autofix = autofix  # Whether to attempt to fix the issue automatically
            
        def get_name(self) -> str:
            """Get the name of the potential issue."""
            if self.name is None:
                return self.__class__.__name__
            return self.name
        
        def subclass_has_resolve_method(self) -> bool:
            """Check if the subclass has a resolve method."""
            return hasattr(self, "resolve") and callable(getattr(self, "resolve"))
        
        def run_resolve(self) -> bool | None:
            """Run the resolve method if it exists."""
            if self.subclass_has_resolve_method():
                return self.resolve() # type: ignore
            return None
        
        def check(self) -> bool:
            """Check if the potential issue exists.
            
            Returns:
                True = issue does not exist.
                False = issue exists.
            
            """
            return False
                
        def to_row(self) -> Tuple[str, str, str]:
            """Do the checks and return a formatted row for the issue."""
            status_icon = self.ICONS.get(self.status, "")
            
            check = self.check()
            if check:
                self.status = self.ICONS["ok"]
            else:
                self.status = self.ICONS["error"]
                if self.subclass_has_resolve_method():
                    if self.autofix:
                        results = self.run_resolve()
                        if results is not None:
                            self.status = self.ICONS["resolvable"] + " " + self.ICONS["right_arrow"] + " " 
                            if results:
                                self.status += self.ICONS["ok"]
                            else:
                                self.status += self.ICONS["error"]
                    else:
                        self.status = self.ICONS["resolvable"] 
                        self.notes.append(f"Rerun with --fix to attempt resolution.")
            
            notes = "\n".join(self.notes) if self.notes else ""

            return (self.get_name(), self.status, notes)

    class UserExists(PotentialIssue):
        def check(self) -> bool: 
            result = db.user_exists(db.get_dcs().username)
            if not result:
                self.notes.append(f"User does not exist in the database: {db.get_dcs().username}.")
                self.notes.append("Run `CREATE USER {db.get_dcs().username} WITH SUPERUSER` to create the user.")
            return result
                
    class UserIsSuperuser(PotentialIssue):
        def check(self) -> bool: 
            result = db.user_is_superuser(db.get_dcs().username)
            if not result:
                self.notes.append(f"User {db.get_dcs().username} is not a superuser.")
            return result

        def resolve(self) -> bool:
            """Attempt to make the user a superuser."""
            try:
                with db.cursor(db="postgres") as cur:
                    cur.execute(f"ALTER USER {db.get_dcs().username} WITH SUPERUSER")
                self.notes.append(f"Fixed: {db.get_dcs().username} is now a superuser.")
                return True
            except psycopg2.Error as e:
                self.notes.append("Run `ALTER USER {db.get_dcs().username} WITH SUPERUSER` to make the user a superuser.")
                return False
            
    class UserOwnsDatabase(PotentialIssue):
        def check(self) -> bool: 
            result = db.user_is_owner_of_db(db.get_dcs().username, db.get_dcs().database)
            if not result:
                self.notes.append(f"User {db.get_dcs().username} is not the owner of the database {db.get_dcs().database}.")
            return result

        def resolve(self) -> bool:
            """Attempt to make the user the owner of the database."""
            try:
                with db.cursor(db="postgres") as cur:
                    cur.execute(f"ALTER DATABASE {db.get_dcs().database} OWNER TO {db.get_dcs().username}")
                self.notes.append(f"Fixed: {db.get_dcs().username} is now the owner of the database {db.get_dcs().database}.")
                return True
            except psycopg2.Error as e:
                self.notes.append("Run `ALTER DATABASE {db.get_dcs().database} OWNER TO {db.get_dcs().username}` to make the user the owner of the database.")
                return False  
            
    class DatabaseExists(PotentialIssue):
        def check(self) -> bool: 
            result = db.get_dcs().database in db.database_names
            if not result:
                self.notes.append(f"Database {db.get_dcs().database} does not exist.")
            return result
        
        def resolve(self) -> bool:
            """Attempt to create the database."""
            try:
                db.create_database(db.get_dcs().database, db.get_dcs().username)
                self.notes.append(f"Fixed: Database {db.get_dcs().database} created with owner {db.get_dcs().username}.")
                return True
            except psycopg2.Error as e:
                self.notes.append(f"Run `CREATE DATABASE {db.get_dcs().database} WITH OWNER {db.get_dcs().username}` to create the database.")
                return False
     
    class RequiredSchemasExist(PotentialIssue):
        def check(self) -> bool:
            """Check if all required schemas exist."""
            self.notes = []
            console.log(f"Checking required schemas: {db.required_schemas}")
            console.log(f"against existing schemas: {db.schema_names}")
            for schema in db.required_schemas:
                if schema not in db.schema_names:
                    self.notes.append(f"Schema {schema} does not exist.")
            return len(self.notes) == 0
        
        def resolve(self) -> bool:
            """Attempt to create all required schemas that don't already exist."""
            try:
                for schema in db.required_schemas:
                    if schema not in db.schema_names:
                        db.create_schema(schema)
                self.notes.append("Fixed: All required schemas created.")
                return True
            except psycopg2.Error as e:
                self.notes.append("Run `CREATE SCHEMA <schema_name>` to create the missing schemas.")
                return False

            
    class UserRequiredGrants(PotentialIssue):
        """Check for ALL PRIVILEGES on various objects in the database."""
        
        def _schema_exists(self, schema: str) -> bool:
            """Check if a schema exists in the database."""
            return schema in db.schema_names
        
        def check(self) -> bool:
            """
            Need to check if any of these 4 are not granted
            GRANT ALL ON SCHEMA schema_name TO username;
            # GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA schema_name TO username;
            # GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA schema_name TO username;
            # GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA schema_name TO username;

            """
            with db.cursor() as cur:
                for schema in db.required_schemas:
                    if schema not in db.schema_names:
                        # Skip schemas that do not exist
                        continue
                    try:
                        # Check for ALL PRIVILEGES on the schema
                        cur.execute(f"SELECT has_schema_privilege('{db.get_dcs().username}', '{schema}', 'USAGE')")
                        result = cur.fetchone()
                        if not result or (result and not result[0]):
                            self.notes.append(f"User {db.get_dcs().username} does not have USAGE privilege on the {schema} schema.")

                        # # Check for ALL PRIVILEGES on all tables in the schema
                        # cur.execute(f"SELECT has_table_privilege('{db.get_dcs().username}', '{schema}', 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')")
                        # result = cur.fetchone()
                        # if not result or (result and not result[0]):
                        #     self.notes.append(f"User {db.get_dcs().username} does not have ALL PRIVILEGES on all tables in the {schema} schema.")

                        # # Check for ALL PRIVILEGES on all sequences in the schema
                        # cur.execute(f"SELECT has_sequence_privilege('{db.get_dcs().username}', '{schema}', 'USAGE, SELECT, UPDATE')")
                        # result = cur.fetchone()
                        # if not result or (result and not result[0]):
                        #     self.notes.append(f"User {db.get_dcs().username} does not have ALL PRIVILEGES on all sequences in the {schema} schema.")

                        # # Check for ALL PRIVILEGES on all functions in the schema
                        # cur.execute(f"SELECT has_function_privilege('{db.get_dcs().username}', '{schema}', 'EXECUTE')")
                        # result = cur.fetchone()
                        # if not result or (result and not result[0]):
                        #     self.notes.append(f"User {db.get_dcs().username} does not have EXECUTE privilege on all functions in the {schema} schema.")
                    except Exception as e:
                        self.notes.append(f"Could not check privileges for schema '{schema}': {e}")
                    
            return len(self.notes) == 0
        
        def resolve(self) -> bool:
            """Attempt to grant all required privileges to the user."""
            try:
                with db.cursor() as cur:
                    for schema in db.required_schemas:
                        cur.execute(f"GRANT ALL ON SCHEMA {schema} TO {db.get_dcs().username}")
                        cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} TO {db.get_dcs().username}")
                        cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema} TO {db.get_dcs().username}")
                        cur.execute(f"GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA {schema} TO {db.get_dcs().username}")
                    
                self.notes.append("Fixed: All required privileges granted to the user.")
                return True
            except psycopg2.Error as e:
                self.notes.append(f"Run the necessary GRANT commands to fix the privileges. Error Occurred: {e}")
                return False
            
    
            
                
    class UserHasAccessToSchemas(PotentialIssue):
        def check(self) -> bool:
            """Check if the user has access to all required schemas."""
            self.notes = []
            for schema in db.required_schemas:
                if not db.user_has_access_to_schema(db.get_dcs().username, schema):
                    self.notes.append(f"User {db.get_dcs().username} does not have access to schema {schema}.")
            return len(self.notes) == 0
        
        def resolve(self) -> bool:
            """Attempt to grant access to all required schemas."""
            try:
                for schema in db.required_schemas:
                    db.grant_schema_privilege("USAGE", schema, db.get_dcs().username)
                    
                self.notes.append("Fixed: User granted access to all required schemas.")
                return True
            except psycopg2.Error as e:
                self.notes.append(f"Run `GRANT USAGE ON SCHEMA <schema_name> TO {db.get_dcs().username}` to grant access to the missing schemas.")
                return False
            
    class ExtensionsInstalled(PotentialIssue):
        def check(self) -> bool:
            """Check if all required extensions are installed."""
            self.notes = []
            required_extensions = db.required_extensions
            available_extensions = db.available_extensions
            
            for ext in required_extensions:
                if ext not in available_extensions:
                    self.notes.append(f"Extension {ext} is not installed on the PostgreSQL server.")
            return len(self.notes) == 0
            
    class ExtensionsCreated(PotentialIssue):
        def check(self) -> bool:
            """Check if all required extensions have been created on the database."""
            notes = []
            required_extensions = db.required_extensions
            installed_extensions = db.installed_extensions

            for ext in required_extensions:
                if ext not in installed_extensions:
                    notes.append(f"Extension {ext} has not been created on the database.")

            self.notes = notes
            return len(notes) == 0
        
        def resolve(self) -> bool:
            """Attempt to create all required extensions."""
            try:
                
                
                for ext in db.required_extensions:
                    db.create_extension(ext, if_not_exists=True)
                self.notes.append("Fixed: All required extensions created.")
                return True
            except psycopg2.Error as e:
                self.notes.append(f"Run `CREATE EXTENSION IF NOT EXISTS <extension_name>` to create the missing extensions. Error Occurred: {e}")
                return False
    
    checks: List[PotentialIssue] = [
        UserExists(fix),
        UserIsSuperuser(fix),
        UserOwnsDatabase(fix),
        DatabaseExists(fix),
        RequiredSchemasExist(fix),
        ExtensionsInstalled(fix),
        ExtensionsCreated(fix),
        UserRequiredGrants(fix),
        UserHasAccessToSchemas(fix),
    ]
    

    
    

    # 1. Database connection info table
    dcs = db.get_dcs()
    conn_table = Table(title="Database Connection Info")
    conn_table.add_column("Key")
    conn_table.add_column("Value")
    conn_table.add_row("Database", dcs.database if dcs else "N/A")
    conn_table.add_row("User", dcs.username if dcs else "N/A")
    conn_table.add_row("Host", dcs.host if dcs else "N/A")
    conn_table.add_row("Port", str(dcs.port) if dcs else "N/A")
    conn_table.add_row("Password", "********" if dcs and dcs.password else "(empty)")

    # 2. Database status table
    check_table = Table(title="Potential Issues Checklist")
    check_table.add_column("Name")
    check_table.add_column("Status")
    check_table.add_column("Notes")
    
    for check in checks:    
        check_table.add_row(*check.to_row())
        
        
    console.print(Group( conn_table, check_table), justify="left")
        
            
        



def main() -> None:
    cli()
