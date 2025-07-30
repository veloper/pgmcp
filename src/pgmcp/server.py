import asyncio

from typing import AsyncGenerator

from fastmcp import Client, FastMCP

from pgmcp.server_age import mcp as age_mcp
from pgmcp.server_crawl import mcp as crawl_mcp
from pgmcp.server_psql import mcp as psql_mcp
from pgmcp.settings import get_settings


# Define Server
mcp = FastMCP(name="pgmcp")

# Mount the AGEService FastMCP server as a subserver
mcp.mount(age_mcp, prefix="age")
mcp.mount(crawl_mcp, prefix="crawl")
mcp.mount(psql_mcp, prefix="psql")

