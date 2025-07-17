from typing import Generator, Tuple

import networkx as nx
import pytest
import pytest_asyncio

from pgmcp.ag_graph import AgGraph
from pgmcp.apache_age import ApacheAGE
from pgmcp.db import AgtypeRecord
from pgmcp.environment import Environment, set_current_env
from pgmcp.settings import get_settings


settings = get_settings()
dbs = settings.db.get_primary()


set_current_env(Environment.TESTING)



@pytest_asyncio.fixture(autouse=True, scope="function")
async def close_sqlalchemy_engine():
    """Fixture to ensure the SQLAlchemy engine is disposed after each test."""
    yield

    await dbs.sqlalchemy_dispose_async_engine()


@pytest.fixture(scope="function")
def nx_graph() -> nx.MultiDiGraph:
    """Fixture to create a sample network for testing (Addams Family).

    Graph
    ```
    Arrows: [▼, ▲, ◀, ▶]
    BoxDrawing: [┌, ┐, └, ┘, ─, ┬, ┴, ├, ┤, ┼]
    OverLines (connecting phonetic symbols): [

                           ┌────────────┐
                           │ Grandmama  │
                           └──┬─────────┘
                  ┌(parent_of)┘    
          ┌───────▼──────┐                  ┌────────────┐
          │    Gomez     ├◀──(married_to)──▶┤  Morticia  │
          └─────┬─┬──────┘                  └────┬─┬─────┘
    ┌(parent_of)┘ └(parent_of)┐  ┌────(parent_of)┘ └(parent_of)┐
    │                         └──┼────────────────┐ ┌──────────┘
    └──────────┐ ┌───────────────┘                │ │
          ┌────▼─▼────┐                     ┌─────▼─▼────┐
          │ Wednesday ├◀───(sibling_to)────▶┤  Pugsley   │
          └───────────┘                     └────────────┘
    ```
    """
    G = nx.MultiDiGraph()
    G.name = "AddamsFamilyNetwork"
    G.add_node("grandmama", label="Human", name="Grandmama")
    G.add_node("gomez", label="Human", name="Gomez Addams")
    G.add_node("morticia", label="Human", name="Morticia Addams")
    G.add_node("wednesday", label="Human", name="Wednesday Addams")
    G.add_node("pugsley", label="Human", name="Pugsley Addams")
    G.add_edge("grandmama", "gomez", label="PARENT_OF")
    G.add_edge("gomez", "morticia", label="MARRIED_TO")
    G.add_edge("morticia", "gomez", label="MARRIED_TO")
    G.add_edge("gomez", "wednesday", label="PARENT_OF")
    G.add_edge("gomez", "pugsley", label="PARENT_OF")
    G.add_edge("morticia", "wednesday", label="PARENT_OF")
    G.add_edge("morticia", "pugsley", label="PARENT_OF")
    G.add_edge("wednesday", "pugsley", label="SIBLING_TO")
    G.add_edge("pugsley", "wednesday", label="SIBLING_TO")
    return G

@pytest.fixture(scope="function")
def ag_graph_dict() -> dict:
    return {
        "name": "AddamsFamilyNetwork",
        "vertices": [
            { "id": 1, "label": "Human", "properties": { "ident": "grandmama", "name": "Grandmama", "age": 70 }, },
            { "id": 2, "label": "Human", "properties": { "ident": "gomez", "name": "Gomez Addams", "age": 42 } },
            { "id": 3, "label": "Human", "properties": { "ident": "morticia", "name": "Morticia Addams", "age": 40 } },
            { "id": 4, "label": "Human", "properties": { "ident": "wednesday", "name": "Wednesday Addams", "age": 12 } },
            { "id": 5, "label": "Human", "properties": { "ident": "pugsley", "name": "Pugsley Addams", "age": 10 } }
        ],
        "edges": [
            { "id": 1, "label": "PARENT_OF", "start_id": 1, "end_id": 2, "properties": { "ident": "grandmama_parent_of_gomez", "start_ident": "grandmama", "end_ident": "gomez", "strained": False} },
            { "id": 2, "label": "MARRIED_TO", "start_id": 2, "end_id": 3, "properties": { "ident": "gomez_married_to_morticia", "start_ident": "gomez", "end_ident": "morticia", "strained": False} },
            { "id": 3, "label": "MARRIED_TO", "start_id": 3, "end_id": 2, "properties": { "ident": "morticia_married_to_gomez", "start_ident": "morticia", "end_ident": "gomez", "strained": False} },
            { "id": 4, "label": "PARENT_OF", "start_id": 2, "end_id": 4, "properties": { "ident": "gomez_parent_of_wednesday", "start_ident": "gomez", "end_ident": "wednesday", "strained": True} },
            { "id": 5, "label": "PARENT_OF", "start_id": 2, "end_id": 5, "properties": { "ident": "gomez_parent_of_pugsley", "start_ident": "gomez", "end_ident": "pugsley", "strained": False} },
            { "id": 6, "label": "PARENT_OF", "start_id": 3, "end_id": 4, "properties": { "ident": "morticia_parent_of_wednesday", "start_ident": "morticia", "end_ident": "wednesday", "strained": False} },
            { "id": 7, "label": "PARENT_OF", "start_id": 3, "end_id": 5, "properties": { "ident": "morticia_parent_of_pugsley", "start_ident": "morticia", "end_ident": "pugsley", "strained": False} },
            { "id": 8, "label": "SIBLING_TO", "start_id": 4, "end_id": 5, "properties": { "ident": "wednesday_sibling_to_pugsley", "start_ident": "wednesday", "end_ident": "pugsley", "strained": True} },
            { "id": 9, "label": "SIBLING_TO", "start_id": 5, "end_id": 4, "properties": { "ident": "pugsley_sibling_to_wednesday", "start_ident": "pugsley", "end_ident": "wednesday", "strained": True} }
        ]
    }

@pytest.fixture(scope="function")
def ag_graph(ag_graph_dict: dict) -> AgGraph:
    """Fixture to create a sample AgGraph for testing."""
    return AgGraph.from_dict(ag_graph_dict)

@pytest.fixture(scope="function")
def agtype_records() -> list[AgtypeRecord]:
    """
    Returns a flat list of AgtypeRecord instances representing the Addams Family graph,
    as if pulled from a Cypher query (vertices and edges mixed, not grouped).
    """
    return [
        # Vertices
        AgtypeRecord(id=1, label="Human", properties={"ident": "grandmama", "name": "Grandmama", "age": 70}),
        AgtypeRecord(id=2, label="Human", properties={"ident": "gomez", "name": "Gomez Addams", "age": 42}),
        AgtypeRecord(id=3, label="Human", properties={"ident": "morticia", "name": "Morticia Addams", "age": 40}),
        AgtypeRecord(id=4, label="Human", properties={"ident": "wednesday", "name": "Wednesday Addams", "age": 12}),
        AgtypeRecord(id=5, label="Human", properties={"ident": "pugsley", "name": "Pugsley Addams", "age": 10}),
        # Edges
        AgtypeRecord(id=11, label="PARENT_OF", start_id=1, end_id=2, properties={"ident": "grandmama_parent_of_gomez", "start_ident": "grandmama", "end_ident": "gomez", "strained": False}),
        AgtypeRecord(id=12, label="MARRIED_TO", start_id=2, end_id=3, properties={"ident": "gomez_married_to_morticia", "start_ident": "gomez", "end_ident": "morticia", "strained": False}),
        AgtypeRecord(id=13, label="MARRIED_TO", start_id=3, end_id=2, properties={"ident": "morticia_married_to_gomez", "start_ident": "morticia", "end_ident": "gomez", "strained": False}),
        AgtypeRecord(id=14, label="PARENT_OF", start_id=2, end_id=4, properties={"ident": "gomez_parent_of_wednesday", "start_ident": "gomez", "end_ident": "wednesday", "strained": True}),
        AgtypeRecord(id=15, label="PARENT_OF", start_id=2, end_id=5, properties={"ident": "gomez_parent_of_pugsley", "start_ident": "gomez", "end_ident": "pugsley", "strained": False}),
        AgtypeRecord(id=16, label="PARENT_OF", start_id=3, end_id=4, properties={"ident": "morticia_parent_of_wednesday", "start_ident": "morticia", "end_ident": "wednesday", "strained": False}),
        AgtypeRecord(id=17, label="PARENT_OF", start_id=3, end_id=5, properties={"ident": "morticia_parent_of_pugsley", "start_ident": "morticia", "end_ident": "pugsley", "strained": False}),
        AgtypeRecord(id=18, label="SIBLING_TO", start_id=4, end_id=5, properties={"ident": "wednesday_sibling_to_pugsley", "start_ident": "wednesday", "end_ident": "pugsley", "strained": True}),
        AgtypeRecord(id=19, label="SIBLING_TO", start_id=5, end_id=4, properties={"ident": "pugsley_sibling_to_wednesday", "start_ident": "pugsley", "end_ident": "wednesday", "strained": True}),
    ]


@pytest_asyncio.fixture(scope="function")
async def apache_age() -> ApacheAGE:
    """Fixture to provide an instance of the ApacheAGE repo."""
    age = ApacheAGE()
    return age
    

@pytest_asyncio.fixture(scope="function")
async def persisted_ag_graph(apache_age: ApacheAGE, ag_graph: AgGraph) -> AgGraph:
    """Fixture to create the same ag_graph but with it persisted in Apache AGE psql test database."""
    await apache_age.ensure_graph(ag_graph.name)
    
    await apache_age.truncate_graph(ag_graph.name)
    
    await apache_age.upsert_graph(ag_graph)
    return ag_graph



@pytest_asyncio.fixture(scope="function")
async def contextmanager_patched_persisted_ag_graph(apache_age: ApacheAGE, persisted_ag_graph: AgGraph) -> Tuple[AgGraph, AgGraph]:
    """Adds Uncle Fester to the persisted graph _instance_ and then applies the patch to it through a contextmanager.
    
    The patch adds Uncle Fester as a sibling of Gomez, a cousin of Morticia, and an uncle to Wednesday and Pugsley.

    ```mermaid        
    graph TD                                         %% Edges + 1 node
        Grandmama -->|PARENT_OF| Gomez               
        Grandmama -->|PARENT_OF| UncleFester         %% NEW
        Gomez ---|SIBLING_OF| UncleFester            %% NEW x 2
        Gomez ---|MARRIED_TO| Morticia             
        Morticia ---|COUSIN_OF| UncleFester          %% NEW
        Gomez -->|PARENT_OF| Wednesday
        Gomez -->|PARENT_OF| Pugsley
        Morticia -->|PARENT_OF| Wednesday
        Morticia -->|PARENT_OF| Pugsley
        UncleFester -->|UNCLE_OF| Wednesday          %% NEW
        UncleFester -->|UNCLE_OF| Pugsley            %% NEW
        Wednesday ---|SIBLING_TO| Pugsley
        Pugsley -->|NIBLING_OF| UncleFester          %% NEW
        Wednesday -->|NIBLING_OF| UncleFester        %% NEW
    ````
    
    """
    base_graph = persisted_ag_graph.deepcopy()
    patched_graph: AgGraph | None = None
    
    # Modify the graph name so that it can be patched without affecting the original persisted graph
    base_graph.name = f"{base_graph.name}_contextmanager_patched"
    
    # Ensure it exists
    await apache_age.ensure_graph(base_graph.name)
    
    # Clear any left over bits.
    await apache_age.truncate_graph(base_graph.name)    
    
    # Persist it under its new name
    base_graph = await apache_age.upsert_graph(base_graph)
    
    # Modify to add Uncle Fester and his relationships
    async with apache_age.patch_graph(base_graph) as graph:
        patched_graph = graph
        
        # uncle_fester is the son of grandmama, the brother of gomez, and the cousin of morticia
        graph.add_vertex("Human", "uncle_fester", properties={"name": "Uncle Fester", "age": 50})
        graph.add_edge("PARENT_OF", "grandmama", "uncle_fester", properties={"strained": False})
        
        graph.add_edge("SIBLING_OF", "uncle_fester", "gomez", properties={"strained": False})
        graph.add_edge("SIBLING_OF", "gomez", "uncle_fester", properties={"strained": False})
        
        graph.add_edge("COUSIN_OF", "morticia", "uncle_fester", properties={"strained": False})
        
        graph.add_edge("UNCLE_OF", "uncle_fester", "wednesday", properties={"strained": False})
        graph.add_edge("UNCLE_OF", "uncle_fester", "pugsley", properties={"strained": False})
        
        graph.add_edge("NIBLING_OF", "pugsley", "uncle_fester", properties={"strained": False})
        graph.add_edge("NIBLING_OF", "wednesday", "uncle_fester", properties={"strained": False})
    
    if not isinstance(patched_graph, AgGraph):
        raise Exception("Patched graph is None, something went wrong with the context manager.")
    
    return base_graph, patched_graph



@pytest_asyncio.fixture(scope="function")
async def awaitable_patched_persisted_ag_graph(apache_age: ApacheAGE, persisted_ag_graph: AgGraph) -> Tuple[AgGraph, AgGraph]:
    """Same as the patched_persisted_ag_graph fixture, but the non contextmanager version.
    
    """
    base_graph = persisted_ag_graph.deepcopy()
    
    
    # Modify the graph name so that it can be patched without affecting the original persisted graph
    base_graph.name = f"{base_graph.name}_awaitable_patched"
    
    # Ensure it exists
    await apache_age.ensure_graph(base_graph.name)
    
    # Clear any left over bits.
    await apache_age.truncate_graph(base_graph.name)    
    
    # Persist it under its new name
    base_graph = await apache_age.upsert_graph(base_graph)
    
    # Patch Graph
    patched_graph: AgGraph = base_graph.deepcopy()
    
    # uncle_fester is the son of grandmama, the brother of gomez, and the cousin of morticia
    patched_graph.add_vertex("Human", "uncle_fester", properties={"name": "Uncle Fester", "age": 50})
    patched_graph.add_edge("PARENT_OF", "grandmama", "uncle_fester", properties={"strained": False})

    patched_graph.add_edge("SIBLING_OF", "uncle_fester", "gomez", properties={"strained": False})
    patched_graph.add_edge("SIBLING_OF", "gomez", "uncle_fester", properties={"strained": False})

    patched_graph.add_edge("COUSIN_OF", "morticia", "uncle_fester", properties={"strained": False})

    patched_graph.add_edge("UNCLE_OF", "uncle_fester", "wednesday", properties={"strained": False})
    patched_graph.add_edge("UNCLE_OF", "uncle_fester", "pugsley", properties={"strained": False})

    patched_graph.add_edge("NIBLING_OF", "pugsley", "uncle_fester", properties={"strained": False})
    patched_graph.add_edge("NIBLING_OF", "wednesday", "uncle_fester", properties={"strained": False})

    # Modify to add Uncle Fester and his relationships
    patched_graph = await apache_age.upsert_graph(patched_graph)

    if not isinstance(patched_graph, AgGraph):
        raise Exception("Patched graph is None, something went wrong with the awaitable.")
    
    return base_graph, patched_graph
