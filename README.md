# PGMCP: PostgreSQL Model Context Protocol

## Overview

This project connects the pgkeen Docker image (with many AI/ML extensions pre-installed) to an MCP server, bridging AI Agents and the Apache AGE graph capabilities of PostgreSQL.


## Architecture

The pgmcp library uses Larman's approach with its design emphasizing high cohesion and low coupling.

### Design
- Asynchronous database operations through asyncpg driver
- Pydantic-based model validation and coercion
- Strict use of Python 3.11+ `typing` features
- Consistent entity naming conventions for improved recall by AI/LLMs
  

### Layers
- **Data**: Apache AGE on PostgreSQL:16
- **Interface**: `ApacheAGE` Python class acting as the repository between Data and Models.
- **Models**: Agnostic Pydantic models (`AgGraph`, `AgVertex`, `AgEdge`, and related classes)
- **Portability**: Simple import/export to and from NetworkX, JSON, and other formats.


### Topology

```shell
AgGraph                  
├── vertices: AgVertices : RootModel[List[AgVertex]]
│   └── AgVertex    
│       ├── ident      : str         # @property -> properties.ident
│       ├── id         : int | None  # AGE managed ID
│       ├── label      : str
│       └── properties : AgProperties : RootModel[Dict[str, Any]]
│           ├── "ident"    : str (required)
│           └── "whatever" : "you want" (Union[str, int, float, bool, None, Dict[...], List[...]])
└── edges: AgEdges : RootModel[List[AgEdge]]
    └── AgEdge
        ├── label       : str 
        ├── ident       : str        # @property -> properties.ident
        ├── start_ident : str        # @property -> properties.start_ident
        ├── end_ident   : str        # @property -> properties.end_ident
        ├── id          : int | None # AGE managed ID
        ├── start_id    : int | None # AGE managed ID
        ├── end_id      : int | None # AGE managed ID
        └── properties  : RootModel[Dict[str, Any]]
            ├── "ident"       : str (required)
            ├── "start_ident" : str (required)
            ├── "end_ident"   : str (required)
            └── "whatever"    : "you want" (Union[str, int, float, bool, None, Dict[...], List[...]])
```

### Identifiers

The identifiers (`Ident`s) are designed to minimize issues with stemming, n-gramming, or tokenization by AIs/LLMs, providing more consistent entity recall.

```python
ident = RoyalDescription.generate(words=3, delimiter="_") # => "magnificent_ancient_king"
```

Identifiers are auto-generated when using the various mutation methods on the `AgGraph`. Alternatively, they can be directly set with those same methods.

### Local Query Building

The API provides a set of chainable query builder helpers, all of which are cached for performance.

```python
# Vertex queries
results : List[AgVertex] = graph.vertices.label("Person").prop("age", 30).all()

# Edge queries  
connections = graph.edges.start_ident("person1").label("KNOWS").all()
```

Checkout `src/pgmcp/ag_query_builder.py` for more info and the available steps and drains.

### NetworkX

You can use `graph.to_networkx()` to gain full access to NetworkX's extensive set of features. When you're done, you can easily convert back using `AgGraph.from_networkx()`.

### Dependencies

- **Python**: >= 3.11 or higher
- **PostgreSQL**: >= 16.0 w/ Apache AGE installed as an additional extension
- **Dependencies**: uv for installation.

### Settings

All settings are managed through environment variables and `.env` files, following `pydantic-settings` rules.

Copy `.env.example` to `.env` and fill in the required values. See Example below:

```
# Application Configuration
APP__LOG_LEVEL=INFO

# DB
DB__CONNECTIONS='{
    "primary": {
        "dsn": "postgresql://username@localhost:5432/db",
        "echo": true|false,
    }
}'

# AGE
AGE__IDENT_PROPERTY="ident"
AGE__START_IDENT_PROPERTY="start_ident"
AGE__END_IDENT_PROPERTY="end_ident"
```
---

## Usage

The primary interface for database operations revolves around the `ApacheAGE` repository class and the `Ag*` classes. See the example usage below:

```python
from pgmcp.apache_age import ApacheAGE
from pgmcp.ag_graph import AgGraph

age = ApacheAGE()

# Create (empty graph)
graph : AgGraph = await age.create_graph("my_graph")
graph : AgGraph = await age.get_or_create_graph("my_graph")

await age.ensure_graph(graph.name)

# Existential 
if await age.graph_exists(graph.name): print("Graph exists!")

# Retrieval
graph_copy = await age.get_graph(graph.name)

# Removal
await age.drop_graph(graph.name)

# Truncation
await age.truncate_graph(graph.name)

# Cypher Queries (low-level)
records = await age.cypher_fetch("my_graph", "MATCH (n) RETURN n")
records = await age.cypher_execute("my_graph", "MATCH (n) DETACH DELETE n")

# Mutation (add vertex)
my_vertex = graph_copy.add_vertex(
    label="Person",
    properties={
        "ident": "john_doe",
        "name": "John Doe",
        "age": 30
    }
)

# Upsert entire graph (if `graph_copy` and `graph` have the same `name`, this will overwrite the existing graph in the database)
updated_graph = await age.upsert_graph(graph_copy)

# To persist a copy under a new name, assign a new name before upserting
graph_copy.name = "my_graph_v2"
updated_graph = await age.upsert_graph(graph_copy)

# Convert to/from models
vertex         : AgVertex = AgVertex.from_agtype_record(record)
back_to_record : AgtypeRecord = vertex.to_agtype_record()

# Convert to/from dict
data_dict        : dict = vertex.to_dict()
record_from_dict : AgVertex = AgVertex.from_dict(data_dict)  # from_dict is a classmethod

# Convert to/from JSON
json_str         : str = vertex.to_json()
record_from_json : AgVertex = AgVertex.from_json(json_str)   # from_json is a classmethod

# Convert to/from NetworkX
nx_graph : nx.MultiDiGraph = graph.to_networkx()
graph_from_nx : AgGraph = AgGraph.from_networkx(nx_graph)
```


## Classes

| Class                  | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| `AgGraph`              | Top-level container for the graph structure.                                |
| `AgEntity`             | Base for vertices and edges.                                                |
| `AgVertex`             | Node object within the graph.                                               |
| `AgEdge`               | Edge object connecting two vertices.                                        |
| `AgProperties`         | Property dictionary for vertices and edges.                                 |
| `AgVertices`           | Collection manager for vertex objects with query helpers.                   |
| `AgEdges`              | Collection manager for edge objects with query helpers.                     |
| `AgMutation`           | Represents an atomic mutation (add, remove, update) on a vertex or edge.    |
| `AgPatch`              | Computes and stores the minimal set of mutations to transform one graph to another. |
| `AgQueryBuilder`       | Chainable, cached query builder for vertices and edges.                     |
| `RoyalDescription`     | Utility for generating canonical, AI-friendly entity identifiers.           |
| `ListRootModel`        | Pydantic root model for lists with graph reference propagation.             |
| `LRUCache`             | Simple least-recently-used cache for query optimization.                    |
| `QueryStringCodec`     | Bidirectional codec for parsing and encoding query strings.                 |
| `DataSourceName`       | Database connection string parser and validator.                            |
| `DatabaseConnectionSettings` | Pydantic model for a single database connection configuration.        |
| `ApacheAGE`            | Repository interface for database operations against Apache AGE/PostgreSQL. |
| `Environment`          | Enum and helpers for environment detection and .env file selection.         |
| `AgtypeRecord`         | Bridge between Python objects and PostgreSQL agtype format.                 |