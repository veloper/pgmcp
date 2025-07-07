import asyncio

from typing import AsyncGenerator

import asyncpg

from fastmcp import Client, FastMCP

from pgmcp.ag_graph import AgGraph
from pgmcp.server_age import mcp as age_mcp
from pgmcp.settings import get_settings


settings = get_settings()
db = settings.db


# Define subserver
mcp = FastMCP(name="pgmcp")

# Mount the AGEService FastMCP server as a subserver
mcp.mount(age_mcp, prefix="age")

