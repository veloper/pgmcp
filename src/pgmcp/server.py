
import asyncio

from typing import AsyncGenerator

import asyncpg

from fastmcp import Client, FastMCP

from pgmcp.ag_graph import AgGraph
from pgmcp.settings import get_settings


settings = get_settings()
db = settings.db


# Define subserver
mcp = FastMCP(name="DynamicService")




@mcp.tool
def initial_tool():
    """Initial tool demonstration."""
    return "Initial Tool Exists"

async def ensure_graph(name: str) -> dict:
    async with db.connection() as conn:
        
        """Ensure a graph exists with the given name."""
        graph = AgGraph.model_validate({"name": name})
        

async def get_or_create_node(graph_name, ident: str) -> dict:
    """Get a node by its identifier."""
    async with db.connection() as conn:
        graph = AgGraph.get_by_ident(ident)
        if not graph:
            raise ValueError(f"Graph with identifier {ident} does not exist.")
        return graph.to_dict()        


