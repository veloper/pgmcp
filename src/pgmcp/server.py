

from fastmcp import FastMCP

from pgmcp.server_crawl import mcp as crawl_mcp
from pgmcp.server_kb import mcp as kb_mcp
from pgmcp.server_psql import mcp as psql_mcp


# Define Server
mcp = FastMCP(name="pgmcp")

# Mount the AGEService FastMCP server as a subserver
mcp.mount(crawl_mcp, prefix="crawl")
mcp.mount(psql_mcp, prefix="psql")
mcp.mount(kb_mcp, prefix="kb")

