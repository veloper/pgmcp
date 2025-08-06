from textwrap import dedent
from typing import Annotated, Any, Dict, List, Literal, Tuple

# Signals
from fastmcp import Client, Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from pgmcp.ag_graph import AgGraph
from pgmcp.apache_age import AgPatch, ApacheAGE
from pgmcp.consts import PG_FUNCTION_ARG_NAME_PATTERN, PG_FUNCTION_NAME_PATTERN, PG_TYPES, PG_TYPES_PATTERN
from pgmcp.settings import get_settings


# =====================================================
# MCP Setup
# =====================================================
mcp = FastMCP(name="PSQL Service")

# =====================================================
# Settings
# =====================================================
settings = get_settings()

# =====================================================
# Database Connection
# =====================================================
dbs = settings.db.get_primary()


# =====================================================
# =====================================================
# Tools
# =====================================================
# =====================================================

# =====================================================
# Select
# =====================================================

@mcp.tool(tags={"psql", "postgresql", "select"})
async def select(
    ctx: Context,
    query: Annotated[str, Field(
        description="The SQL query to execute against the primary PostgreSQL database with placeholders for corresponding parameter keys.",
        examples=["SELECT * FROM users WHERE id = :user_id AND status = :status"]
    )],
    params: Annotated[Dict[str, Any], Field(
        description="Dictionary of parameters to pass to the SQL query.",
        examples=[{"user_id": 1, "status": "active"}],
    )] = {}

) -> List[Dict[str, Any]]:
    """Execute a SQL query against the primary PostgreSQL database and return a List[Dict[str, Any]] of rows."""
    
    async with dbs.sqlalchemy_transaction() as conn:
        if not query.strip().lower().startswith(("select", "with")):
            raise ValueError("Only SELECT queries are allowed in this tool.")
        return await dbs.fetch(query, params)

# =========================================================
# Delete
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "delete"})
async def delete(
    ctx: Context,
    query: Annotated[str, Field(
        description="The SQL DELETE query to execute against the primary PostgreSQL database with placeholders for corresponding parameter keys.",
        examples=["DELETE FROM users WHERE id = :user_id"]
    )],
    params: Annotated[Dict[str, Any], Field(
        description="Dictionary of parameters to pass to the SQL DELETE query.",
        examples=[{"user_id": 1}]
    )] = {}
) -> None:
    """Execute a SQL DELETE query against the primary PostgreSQL database."""
    async with dbs.sqlalchemy_transaction() as conn:
        if not query.strip().lower().startswith("delete"):
            raise ValueError("Only DELETE queries are allowed in this tool.")
        await dbs.execute(query, params)
        
# =========================================================
# Insert
# =========================================================
        
@mcp.tool(tags={"psql", "postgresql", "insert"})
async def insert(
    ctx: Context,
    query: Annotated[str, Field(
        description="The SQL INSERT query to execute against the primary PostgreSQL database with placeholders for corresponding parameter keys.",
        examples=["INSERT INTO users (name, email) VALUES (:name, :email)"]
    )],
    params: Annotated[Dict[str, Any], Field(
        description="Dictionary of parameters to pass to the SQL INSERT query.",
        examples=[{"name": "John Doe", "email": "john.doe@example.com"}]
    )] = {}
) -> None:
    """Execute a SQL INSERT query against the primary PostgreSQL database."""
    async with dbs.sqlalchemy_transaction() as conn:
        if not query.strip().lower().startswith("insert"):
            raise ValueError("Only INSERT queries are allowed in this tool.")
        await dbs.execute(query, params)
        
# =========================================================
# Update
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "update"})
async def update(
    ctx: Context,
    query: Annotated[str, Field(
        description="The SQL UPDATE query to execute against the primary PostgreSQL database with placeholders for corresponding parameter keys.",
        examples=["UPDATE users SET status = :status WHERE id = :user_id"]
    )],
    params: Annotated[Dict[str, Any], Field(
        description="Dictionary of parameters to pass to the SQL UPDATE query.",
        examples=[{"user_id": 1, "status": "inactive"}]
    )] = {}
) -> None:
    """Execute a SQL UPDATE query against the primary PostgreSQL database."""
    async with dbs.sqlalchemy_transaction() as conn:
        if not query.strip().lower().startswith("update"):
            raise ValueError("Only UPDATE queries are allowed in this tool.")
        await dbs.execute(query, params)
        
# =========================================================
# Upsert
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "upsert"})
async def upsert(
    ctx: Context,
    query: Annotated[str, Field(
        description="The SQL UPSERT query to execute against the primary PostgreSQL database with placeholders for corresponding parameter keys.",
        examples=["INSERT INTO users (id, name) VALUES (:id, :name) ON CONFLICT (id) DO UPDATE SET name = :name"]
    )],
    params: Annotated[Dict[str, Any], Field(
        description="Dictionary of parameters to pass to the SQL UPSERT query.",
        examples=[{"id": 1, "name": "Jane Doe"}]
    )] = {}
) -> None:
    """Execute a SQL UPSERT _Style_ query against the primary PostgreSQL database using the ON CONFLICT UPDATE clause."""
    async with dbs.sqlalchemy_transaction() as conn:
        lc_query = query.strip().lower()
        if not lc_query.startswith("insert"):
            raise ValueError("Must start with 'INSERT' for UPSERT queries.")
        if "on conflict" not in lc_query:
            raise ValueError("UPSERT queries must include an 'ON CONFLICT' clause.")
        await dbs.execute(query, params)

# =========================================================
# Create Extension
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "extension", "create"}, annotations=ToolAnnotations(idempotentHint=True))
async def create_extension_if_not_exists(
    ctx: Context,
    extension_name: str
) -> None:
    """Create a new extension in the PostgreSQL database."""
    query = f"CREATE EXTENSION IF NOT EXISTS {extension_name}"
    await dbs.execute(query)

# =========================================================
# Create Function
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "function", "create"}, annotations=ToolAnnotations(idempotentHint=True))
async def create_or_replace_function(
    ctx: Context,
    sql: Annotated[str, Field(
        description="The SQL function definition to create or replace in the PostgreSQL database.",
        examples=[dedent("""
            CREATE OR REPLACE FUNCTION my_function(arg1 INTEGER, arg2 TEXT)
            RETURNS VOID AS $$
            BEGIN
                -- Function logic goes here 
            END;
            $$ LANGUAGE plpgsql;
        """)]
    )],
) -> None:
    """Create or replace a function in the PostgreSQL database."""
    
    if not sql.strip().lower().startswith("create or replace function"):
        raise ValueError("SQL must start with 'CREATE OR REPLACE FUNCTION' for function creation.")
    await dbs.execute(sql)

# =========================================================
# Drop Function
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "function", "drop"})
async def drop_function( ctx: Context, function_name: Annotated[str, Field(pattern=PG_FUNCTION_NAME_PATTERN)]) -> None:
    """Drop a function from the PostgreSQL database by its name. """
    query = f"DROP FUNCTION IF EXISTS {function_name}()"
    await dbs.execute(query)

# =========================================================
# List Functions
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "function"})
async def list_functions( ctx: Context, schema: Annotated[str, Field("public", description="db schema", examples=["public"] )] = "public" ) -> List[str]:
    """List all functions in the specified PostgreSQL schema."""
    query = f"""
    SELECT routine_name
    FROM information_schema.routines 
    WHERE specific_schema = :schema 
    AND routine_type = 'FUNCTION'
    """
    result = await dbs.fetch(query, {"schema": schema})
    return [row["routine_name"] for row in result]

# =========================================================
# pg_http extension: Request (blocking call)
# =========================================================

@mcp.tool(tags={"psql", "postgresql", "http", "request"})
async def http_request(
    ctx: Context,
    url: Annotated[str, Field(
        description="The URL to send the HTTP request to.",
        examples=["https://api.example.com/data"]
    )],
    method: Annotated[str, Field(
        description="The HTTP method to use for the request.",
        examples=["GET", "POST"]
    )] = "GET",
    headers: Annotated[Dict[str, str], Field(
        description="Headers to include in the HTTP request.",
        examples=[{"Authorization": "Bearer token"}]
    )] = {},
    body: Annotated[Dict[str, Any], Field(
        description="The body of the HTTP request.",
        examples=[{"key": "value"}]
    )] = {}
) -> Any:
    """Use the pg_http extension to make an HTTP request from PostgreSQL and return the HTTP_RESPONSE type object. """
    query = f"SELECT pg_http.request( url := :url, method := :method, headers := :headers, body := :body) "
    return await dbs.fetch(query, {"url": url, "method": method, "headers": headers, "body": body})



