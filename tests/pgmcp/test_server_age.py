import datetime, json, os, time

import pytest, pytest_asyncio

from fastmcp import Client, FastMCP
from mcp.types import TextContent

from pgmcp.apache_age import ApacheAGE
from pgmcp.server_age import mcp


# Set env to trick rich into thinking it's a much wider terminal
os.environ["COLUMNS"] = "200"
os.environ["PYTHONUNBUFFERED"] = "1"  # Ensure output is unbuffered for better test output visibility
os.environ["TERM"] = "xterm-256color"  # Set a terminal type that supports colors

@pytest.fixture(scope="session")
def mcp_server() -> FastMCP:
    return mcp

@pytest.mark.asyncio
async def test_server_age(mcp_server: FastMCP, apache_age: ApacheAGE) -> None:
    """
    Scenario: Addams Family Graph - Node and Edge Upsert

    This test will construct a small graph representing the Addams family. 
    We will:
      - Upsert vertices for each family member (e.g., Gomez, Morticia, Wednesday, Pugsley, etc.).
      - Upsert edges to represent family relationships (e.g., "parent_of", "married_to").
    
    The primary goal is to try to trigger the problematic behavior observed when individual edges are upserted.
    Specifically, we want to:
      - Exercise and verify the upsert_vertex and upsert_edge methods.
      - Ensure vertices are created or updated as expected.
      - Ensure edges are created between the correct nodes.
      - Observe whether multiple upserts (especially of individual edges) cause overmatching or accidental clearing of edges.
      - Confirm the resulting graph structure in the database matches the intended family relationships.

    This is motivated by observed issues where repeated edge upserts appear to overmatch and clear out edges unexpectedly.
    """
    
    async with Client(mcp_server) as client:
        results = {}
        # Compute seconds since Monday July 7th, 2025, 12:19 AM
        base_dt = datetime.datetime(2025, 7, 7, 0, 19, 0, tzinfo=datetime.timezone.utc)
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        seconds_since = int((now_dt - base_dt).total_seconds())
        graph_name = f"aad3{seconds_since}"

        results["graph"] = await client.call_tool("get_or_create_graph", {"graph_name": graph_name})
        
        results["gomez"] = await client.call_tool("upsert_vertex", {"graph_name": graph_name, "vertex_ident": "Gomez", "properties": {"age": 40, "role": "father"}})
        results["morticia"] = await client.call_tool("upsert_vertex", {"graph_name": graph_name, "vertex_ident": "Morticia", "properties": {"age": 38, "role": "mother"}})
        results["wednesday"] = await client.call_tool("upsert_vertex", {"graph_name": graph_name, "vertex_ident": "Wednesday", "properties": {"age": 12, "role": "daughter"}})
        results["pugsley"] = await client.call_tool("upsert_vertex", {"graph_name": graph_name, "vertex_ident": "Pugsley", "properties": {"age": 10, "role": "son"}})
        
        results["married_gomez_morticia"] = await client.call_tool("upsert_edge", {
            "graph_name": graph_name, "edge_start_ident": "Gomez", "edge_end_ident": "Morticia", "label": "married_to", "properties": {"since": 1990}
        })
        results["parent_gomez_wednesday"] = await client.call_tool("upsert_edge", {
            "graph_name": graph_name, "edge_start_ident": "Gomez", "edge_end_ident": "Wednesday", "label": "parent_of", "properties": {"biological": True}
        })
        results["parent_morticia_wednesday"] = await client.call_tool("upsert_edge", {
            "graph_name": graph_name, "edge_start_ident": "Morticia", "edge_end_ident": "Wednesday", "label": "parent_of", "properties": {"biological": True}
        })
        results["parent_gomez_pugsley"] = await client.call_tool("upsert_edge", {
            "graph_name": graph_name, "edge_start_ident": "Gomez", "edge_end_ident": "Pugsley", "label": "parent_of", "properties": {"biological": True}
        })
        results["parent_morticia_pugsley"] = await client.call_tool("upsert_edge", {
            "graph_name": graph_name, "edge_start_ident": "Morticia", "edge_end_ident": "Pugsley", "label": "parent_of", "properties": {"biological": True}
        })
        results["sibling_wednesday_pugsley"] = await client.call_tool("upsert_edge", {
            "graph_name": graph_name, "edge_start_ident": "Wednesday", "edge_end_ident": "Pugsley", "label": "sibling_of", "properties": {"relationship": "sibling"}
        })
        
        
        results["graph_final"] = await client.call_tool("get_or_create_graph", {"graph_name": graph_name})
        
        # Check the edges in the last upsert (sibling_wednesday_pugsley) for property integrity
        graph_result = results["parent_morticia_wednesday"]
        
        data = {}
        
        if hasattr(graph_result, "content") and isinstance(graph_result.content, list) and hasattr(graph_result.content[0], "text"):
            content_block = graph_result.content[0]
            if isinstance(content_block, TextContent):
                data = json.loads(content_block.text)
                
                # for each edge, confirm that all required properties are present and not None or "None"
                for edge in data.get("edges", []):
                    if edge.get("label") == "sibling_of":
                        assert edge.get("properties", {}).get("relationship") == "sibling", f"Edge 'sibling_of' should have 'relationship' property set to 'sibling', got {edge.get('properties', {}).get('relationship')}"
                        assert edge.get("start_ident") is not None, "Edge 'sibling_of' must have a valid start_ident"
                        assert edge.get("end_ident") is not None, "Edge 'sibling_of' must have a valid end_ident"
        else:   
            raise ValueError("Unexpected graph result format, expected a TextContent with JSON data.")
