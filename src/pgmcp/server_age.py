import json, re

from pathlib import Path
from textwrap import dedent
from typing import Annotated, Any, Dict, List

# Signals
from blinker import Namespace
from bs4 import BeautifulSoup
from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field
from pyvis.network import Network

from pgmcp.ag_graph import AgGraph
from pgmcp.apache_age import AgPatch, ApacheAGE


# =====================================================
# MCP Setup
# =====================================================
mcp = FastMCP(name="AGEService")

# =====================================================
# Apache AGE Repository
# =====================================================
age = ApacheAGE()


# =====================================================
# Blinker Signals & Handlers
# =====================================================
signals = Namespace()

mutation_signal = signals.signal("mutation")

@mutation_signal.connect
async def on_mutation(sender: Any, ctx : Context, graph: AgGraph) -> None:
    """Signal handler for mutation events."""
    await ctx.log(f"Mutation event triggered by {sender!r}.", level="info")
    try:
        html_path = await _write_visjs_single_page_html_app_to_file(graph)
        await ctx.log(f"Graph visualization HTML written to {html_path!r}.", level="info")
    except Exception as e:
        await ctx.log(f"Error writing graph visualization HTML: {e} SUPPRESSED!", level="info")
    
# =====================================================
# Constants
# =====================================================

# Updated pattern: allow alphanum, underscore, dash, dot, and slash for graph names and idents
GRAPH_NAME_PATTERN = r"^[a-zA-Z0-9§_/]+$"
IDENT_PATTERN = GRAPH_NAME_PATTERN  # Same pattern for idents

# =====================================================
# Helper Functions
# =====================================================

async def _write_visjs_single_page_html_app_to_file( graph: AgGraph ) -> Path:
    """Write a single-page HTML file using vis.js's Network to visualize the graph."""
    nt = Network( height="1000px", width="100%", bgcolor="#FFFFFF", font_color="black", select_menu=True, filter_menu=True ) # type: ignore

    if not graph.vertices or not graph.edges:
        nt.add_node("empty", label="No Data", color="#FF0000", title="No vertices or edges available")
        return Path("/dev/null")  # Return a dummy path if no data is present
        

    vertex_ident_to_data: Dict[str, Any] = {
        vertex.ident: {
            "ident": vertex.ident,
            "label": vertex.label,
            "properties": vertex.properties.model_dump_json(indent=2),
        } for vertex in graph.vertices
    }
    
    edge_ident_to_data: Dict[str, Any] = {
        f"{edge.start_ident}->{edge.end_ident}": {
            "label": edge.label,
            "properties": edge.properties.model_dump_json(indent=2),
            "start_ident": edge.start_ident,
            "end_ident": edge.end_ident
        } for edge in graph.edges
    }
    
    vertex_ident_to_data_json = json.dumps(vertex_ident_to_data, indent=2)
    edge_ident_to_data_json = json.dumps(edge_ident_to_data, indent=2)

    head_script = dedent("""
        function HTMLTitle(html) {
            let div = document.createElement('div');
            div.innerHTML = html;
            return div;
        }
        
        const vertex_ident_to_data = [[[vertex_ident_to_data_json]]];
        const edge_ident_to_data = [[[edge_ident_to_data_json]]];

        // Let js generate all the html, we'll provide the data from the backend
        function table_template(ident) {
            const data = vertex_ident_to_data[ident] || edge_ident_to_data[ident];
            return HTMLTitle(`
                <div>
                    <table>
                        <tr><th>Label</th><td>${data.label}</td></tr>
                        <tr><th>ID</th><td>${data.ident}</td></tr>` + 
                        ( data.start_ident ? '<tr><th>Start ID</th><td>${data.start_ident}</td></tr>' : '' ) + 
                        ( data.end_ident ? '<tr><th>End ID</th><td>${data.end_ident}</td></tr>' : '' ) + 
                        `<tr colspan=2><th>Properties</th></tr>
                        <tr><td colspan=2>
                            <pre>${data.properties}</pre>
                        </td></tr>
                    </table>
                </div>
            `);
        }
    """)
    
    head_script = head_script.replace("[[[vertex_ident_to_data_json]]]", vertex_ident_to_data_json)
    head_script = head_script.replace("[[[edge_ident_to_data_json]]]", edge_ident_to_data_json)

    for vertex in graph.vertices:
        nt.add_node(vertex.ident, label=vertex.ident, color="#eeffa0", title=f"<<<{vertex.ident}>>>")

    for edge in graph.edges:
        ident = f"{edge.start_ident}->{edge.end_ident}"
        nt.add_edge(edge.start_ident, edge.end_ident, label=edge.label, color="#6161614D", title=f"<<<{ident}>>>")

    html_dir = Path("/tmp/pgmcp")
    html_dir.mkdir(parents=True, exist_ok=True)
    
    html_path = html_dir / f"{graph.name}.html"

    nt.cdn_resources = "in_line"  # Use CDN for resources
    nt.write_html(html_path.as_posix(), local=True, notebook=False, open_browser=False)
    
    html = html_path.read_text(encoding='utf-8')
    
    soup = BeautifulSoup(html, 'html.parser')

    # Inject Script
    script_tag = soup.new_tag("script")
    script_tag.string = head_script
    if el := soup.head or soup.body:
        el.append(script_tag)

    html = str(soup)

    # find all of the <<<ident>>> strings which will appear in the raw 
    # html as \b<<<(?.+?)>>>\b, and sub it with simple `table_template($0)`
    
    html = re.sub(r'\b<<<(.+?)>>>\b', r'table_template("\1")', html)

    html_path.write_text(html, encoding='utf-8')
    
    return html_path

# =====================================================
# =====================================================
# Tools
# =====================================================
# =====================================================


# ====================================================================
# TOOL: generate_visualization
# ====================================================================
@mcp.tool(tags={"graph", "visualization", "pyvis", "vis.js"}, annotations=ToolAnnotations(idempotentHint=True))
async def generate_visualization(
    ctx: Context, 
    graph_name: Annotated[str, Field( description="Name of the graph to visualize", min_length=1, max_length=128, pattern=GRAPH_NAME_PATTERN )]
) -> str:
    """Generate a single page html file using vis.js's Network to visualize any graph.

    Args:
        ctx: The request context.
        graph_name: The name of the graph to visualize.

    Returns:
        The path to the generated HTML file.
    """
    
    graph = await age.get_graph(graph_name)

    file_path = await _write_visjs_single_page_html_app_to_file(graph)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    return f"Run this from the command line to view the network web page: `open -a \"Google Chrome\" file://{file_path}`"


# ====================================================================
# TOOL: drop_graphs
# ====================================================================

@mcp.tool(tags={"graph", "drop", "mutation"}, annotations=ToolAnnotations(idempotentHint=False))
async def drop_graphs(
    ctx: Context,
    graph_names: Annotated[ List[str], Field( 
        description="A list of exact graph names to drop. ", 
        json_schema_extra={ "type": "array", "items": { "type": "string" } } 
    )]
) -> dict:
    """
    Drop one or more graphs by graph_name.

    Args:
        graph_names: Names of the graphs to drop.

    LLM Usage:
    - Use to remove graphs and all their associated data.
    - Returns: Confirmation of the graph drop operation.
    """
    for graph_name in graph_names:
        await age.drop_graph(graph_name)
    return {"status": "success", "graph_names": graph_names}

# ====================================================================
# TOOL: list_graphs
# ====================================================================

@mcp.tool(tags={"graph", "list", "metadata"})
async def list_graphs(ctx: Context) -> list[str]:
    """
    List all graph names in the database.
    
    LLM Usage:
    - Use to enumerate all available graph names managed by Apache AGE/PostgreSQL.
    - Returns: List of graph name strings.
    - Typical next step: select a graph for further operations (e.g., get_graph, add_vertex).
    """
    return await age.get_graph_names()

# ====================================================================
# TOOL: get_or_create_graph
# ====================================================================

@mcp.tool(tags={"graph", "create", "mutation"}, annotations=ToolAnnotations( idempotentHint=True ))
async def get_or_create_graph(
    ctx: Context,
    graph_name: Annotated[str, Field(description="Name of the graph", min_length=1, max_length=128, pattern=GRAPH_NAME_PATTERN)]
) -> dict:
    """
    Get or create a graph with the specified name.
    
    Args:
        graph_name: Name of the graph to retrieve or create.
    
    LLM Usage:
    - Use to ensure a graph exists before performing operations on it.
    - Returns: Graph metadata as a dict (name, idents, etc.).
    - If the graph does not exist, it will be created.
    """
    
    graph = await age.get_or_create_graph(graph_name)
    
    await mutation_signal.send_async("get_or_create_graph", ctx=ctx, graph=graph)
    
    return graph.model_dump()

# ====================================================================
# TOOL: upsert_vertex
# ====================================================================

@mcp.tool(tags={"vertex", "insert", "upsert", "mutation"}, annotations=ToolAnnotations(idempotentHint=True))
async def upsert_vertex(
    ctx: Context,
    graph_name : Annotated[str, Field(description="Unique name of the graph where the vertex exists", min_length=1, max_length=128, pattern=GRAPH_NAME_PATTERN)],
    vertex_ident : Annotated[str, Field(description="Unique ident of the vertex to update", min_length=1, max_length=128, pattern=IDENT_PATTERN)],
    label: Annotated[str, Field(description="Label of the vertex", min_length=1, max_length=256)] | None = None,
    properties: Annotated[dict, Field(
        description="Properties to add or update on the vertex", 
        json_schema_extra={
            "type": "object",
            "additionalProperties": True,
            "description": "Key-value pairs to add or update on the vertex."
        } 
    )] | None = None
                                      
) -> Dict[str, Any]:
    """
    Update or insert a vertex's properties in a graph non-destructively.

    Args:
        graph_name: Name of the graph where the vertex exists.
        vertex_ident: Unique ident of the vertex to update.
        label: Label of the vertex (optional).
        properties: Properties to add or update on the vertex (optional).

    Returns:
        Full representation of the graph after the upsert operation.

    LLM Usage:
    - Use to:
        - update or insert a vertex's properties or label in a graph.
        - insert a new vertex if it does not exist.
    
    """
    graph = await age.get_graph(graph_name)

    if not (vertex := graph.get_vertex_by_ident(vertex_ident)):
        vertex = graph.add_vertex(
            label if label else "Node",
            vertex_ident,
            properties=properties or {}
        )

    plan = {}
    if properties: plan["properties"] = properties
    if label: plan["label"] = label
    vertex.upsert(**plan)
    
    updated_graph = await age.upsert_graph(graph)
    if not updated_graph:
        raise Exception(f"Graph '{graph_name}' not found after upsert operation. Possible asynchronous operation dropped or modified during this operation.")

    await mutation_signal.send_async("upsert_vertex", ctx=ctx, graph=graph)

    return updated_graph.model_dump()

# ====================================================================
# TOOL: upsert_edge
# ====================================================================

@mcp.tool(tags={"edge", "insert", "upsert", "mutation"}, annotations=ToolAnnotations(idempotentHint=True))
async def upsert_edge(
    ctx: Context,
    graph_name: Annotated[str, Field(description="Unique name of the graph where the edge exists", min_length=1, max_length=128, pattern=GRAPH_NAME_PATTERN)],
    label: Annotated[str, Field(description="Label of the edge", min_length=1, max_length=256)],
    edge_start_ident: Annotated[str, Field(description="Unique ident of the start vertex", min_length=1, max_length=128, pattern=IDENT_PATTERN)],
    edge_end_ident: Annotated[str, Field(description="Unique ident of the end vertex", min_length=1, max_length=128, pattern=IDENT_PATTERN)],
    properties: Annotated[dict, Field(
        description="Properties to add or update on the edge", 
        json_schema_extra={
            "type": "object",
            "additionalProperties": True,
            "description": "Key-value pairs to add or update on the edge."
        } 
    )] | None = None
) -> Dict[str, Any]:
    """
    Update a graph's edge's properties non-destructively (only adds or updates existing properties).
    
    Important: 
        This cannot be used to change the start or end vertex of an edge. Instead use 
        drop_edge and then you may use this to upsert a new edge _correct_ edge.
        
        This is due to the fact that this is used as a composite key for the edge specification:
        [graph_name, label, edge_start_ident, edge_end_ident] is the unique identifier for an edge 
        in Apache AGE.

    Args:
        graph_name: Name of the graph where the edge exists.
        label: Label of the edge.
        edge_start_ident: Unique ident of the start vertex.
        edge_end_ident: Unique ident of the end vertex.
        properties: Properties to add or update on the edge.

    Returns:
        Full representation of the graph after the upsert operation.

    LLM Usage:
    - Use to:
        - update or insert an edge's properties in a graph.
        - insert a new edge if it does not exist.
    """
    graph = await age.get_graph(graph_name)

    if (edge := graph.edges.start_ident(edge_start_ident).end_ident(edge_end_ident).label(label).first()):
        edge.label = label
        for key, value in (properties or {}).items():
            edge.properties[key] = value
        await ctx.log(f"Edge {edge_start_ident}->{edge_end_ident} was found to exist and updated with properties: {properties} and label: {label}", level="info")
    else:
        edge = graph.add_edge( label, edge_start_ident, edge_end_ident, properties=properties or {})
        await ctx.log(f"Edge {edge_start_ident}->{edge_end_ident} was not found, so a new edge was created with properties: {properties} and label: {label}", level="info")
        
    
    updated_graph = await age.upsert_graph(graph)
    if not updated_graph:
        raise Exception(f"Graph '{graph_name}' not found after upsert operation. Possible asynchronous operation dropped or modified during this operation.")

    await mutation_signal.send_async("upsert_edge", ctx=ctx, graph=graph)

    return updated_graph.model_dump()

# ====================================================================
# TOOL: drop_vertex
# ====================================================================

@mcp.tool(tags={"vertex", "remove", "mutation"})
async def drop_vertex(
    ctx: Context,
    graph_name: Annotated[str, Field(description="Name of the graph", min_length=1, max_length=128, pattern=GRAPH_NAME_PATTERN)],
    vertex_ident: Annotated[str, Field(description="Unique ident of the vertex to remove", min_length=1, max_length=128, pattern=IDENT_PATTERN)]
) -> str:
    """
    Remove a vertex by ident.
    
    Args:
        graph_name: Name of the graph.
        vertex_ident: Unique ident of the vertex to remove.
        
    LLM Usage:
    - Use to delete a node from the graph by its ident.
    - Returns: Confirmation string or not-found message.
    - Edges connected to this vertex may also be removed.
    """
    graph = await age.get_graph(graph_name)
    vertex = graph.get_vertex_by_ident(vertex_ident)
    if not vertex:
        raise Exception(f"Vertex with ident '{vertex_ident}' not found in graph '{graph_name}', maybe you didn't use the correct vertex ident?")
    
    graph.remove_vertex(vertex)
    
    await age.upsert_graph(graph)
    
    await mutation_signal.send_async("drop_vertex", ctx=ctx, graph=graph)
    
    return f"Vertex '{vertex_ident}' removed."
    
    

# ====================================================================
# TOOL: drop_edge
# ====================================================================

@mcp.tool(tags={"edge", "remove", "mutation"})
async def drop_edge(
    ctx: Context,
    graph_name: Annotated[str, Field(description="Name of the graph", min_length=1, max_length=128, pattern=GRAPH_NAME_PATTERN)],
    edge_ident: Annotated[str, Field(description="Unique ident of the edge to remove", min_length=1, max_length=128, pattern=IDENT_PATTERN)],
) -> str:
    """Drop an edge by its ident.
    
    Args:
        graph_name: Name of the graph.
        edge_ident: Unique ident of the edge to remove.

    LLM Usage:
    - Use to delete an edge from the graph by its ident.
    - Returns: Confirmation string or not-found message.
    """
    graph = await age.get_graph(graph_name)
    edge = graph.get_edge_by_ident(edge_ident)
    if not edge:
        return f"Edge '{edge_ident}' not found in graph '{graph_name}', maybe you didn't use the correct edge ident?"
    graph.remove_edge(edge)
    
    await age.upsert_graph(graph)
    
    await mutation_signal.send_async("drop_edge", ctx=ctx, graph=graph)
    
    return f"Edge '{edge_ident}' removed."




@mcp.tool(tags={"graph", "mutation", "upsert"}, annotations=ToolAnnotations(idempotentHint=True))
async def upsert_graph(
    ctx: Context,
    graph_name: Annotated[str, Field(description="Name of the graph", min_length=1, max_length=128, pattern=GRAPH_NAME_PATTERN)],
    vertices: Annotated[List[dict], Field(
        description="List of vertex dicts to upsert", 
        json_schema_extra={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "The _type_ of vertex akin to a model name.",
                        "minLength": 1,
                        "maxLength": 128,
                        "example": ["person", "idea", "organization", "location", "event", "node", "goal", "task", "project", "concept", "has_many", "has_one", "belongs_to", "part_of", "owns", "child_of", "parent_to"],
                    },
                    "ident": {
                        "type": "string",
                        "description": "Primary unique ident for the vertex. If not provided, a new one will be generated."
                    },
                    "properties": {
                        "type": "object",
                        "description": "Key-value properties for the vertex akin to a model's attributes.",
                        "additionalProperties": True
                    }
                },
                "required": ["label", "properties"],
                "additionalProperties": False
            }
        },
    )],
    edges: Annotated[List[dict], Field(
        description="List of edge dicts to upsert",
        json_schema_extra={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ident": {
                        "type": "string",
                        "description": "Optional unique ident for the edge",
                        "minLength": 1,
                        "maxLength": 128,
                        "pattern": IDENT_PATTERN
                    },
                    "start_ident": {
                        "type": "string",
                        "description": "Identifier of the start vertex",
                        "minLength": 1,
                        "maxLength": 128,
                        "pattern": IDENT_PATTERN,
                    },
                    "end_ident": {
                        "type": "string",
                        "description": "Identifier of the end vertex",
                        "minLength": 1,
                        "maxLength": 128,
                        "pattern": IDENT_PATTERN
                    },
                    "label": {
                        "type": "string",
                        "description": "Edge label",
                        "example": [ "PARENT_TO", "CHILD_OF", "PART_OF", "OWNS", "BELONGS_TO", "HAS_MANY", "HAS_ONE"],
                    },
                    "properties": {
                        "type": "object",
                        "description": "Key-value properties for the edge",
                        "additionalProperties": True
                    }
                },
                "required": ["label", "start_ident", "end_ident", "properties"],
                "additionalProperties": False
            }
        }
    )]
) -> dict:
    """
    Upserts both Vertices and Edges into the specified graph_name.

    This is a _hammer_ operation: it will deeply merge the provided vertices and edges into the existing graph, overwriting or adding as needed. Use with care.

    LLM Instructions:
        1. Use Chain of Through to represent an internal monolog that is vocalized.
        2. Use _Speech Act Theory_ to determine the _Illocutionary Force_ of the user's utterances.
        3. Determine the _Perlocutionary Effect_ expected by the user regarding the graph and how they expect it to change.
        4. Use the insights from steps 1-3 to present a crystalized synthesis of your thinking to the user, taking the form of a plan of action.
        5. Immediately use the insights and planning of the previous steps to form the parameters you generate for this tool, and execute it.

    Important:
        - This operation does not create a new graph if it does not exist; it will raise an error instead.
        - Vertices and edges are matched by their unique identifiers and labels. Existing properties will be updated or merged, and new ones will be added.
        - Edges are uniquely identified by [graph_name, label, start_ident, end_ident]. Changing the start or end vertex of an edge requires deleting and recreating the edge.

    Args:
        graph_name: Name of the graph to upsert into.
        vertices: List of vertex dicts to upsert. Each dict should include at least 'label' and 'properties'.
        edges: List of edge dicts to upsert. Each dict should include 'label', 'start_ident', 'end_ident', and 'properties'.

    Returns:
        The updated graph metadata as a dict.

    LLM Usage:
    - Use to:
        - Merge or update multiple vertices and edges in an existing graph in a single operation.
        - Add new vertices or edges if they do not exist.
        - Deeply update properties of existing vertices and edges.
    - Does NOT create a new graph if the specified graph does not exist.
    - Returns: The updated graph metadata as a dict.
"""
    graph = await age.get_graph(graph_name)
    if not graph:
        raise ValueError(f"Graph '{graph_name}' does not exist. Make sure you're using the correct graph name.")
    
    graph = graph.deepcopy()

    for vertex_data in vertices:
        graph.upsert_vertex(vertex_data)

    for edge_data in edges:
        graph.upsert_edge(edge_data)

    merged_graph = await age.upsert_graph(graph)

    await mutation_signal.send_async("upsert_graph", ctx=ctx, graph=merged_graph)

    return merged_graph.model_dump()

