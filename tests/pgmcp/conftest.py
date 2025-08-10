from contextlib import contextmanager
from textwrap import dedent
from typing import Generator, Tuple

import networkx as nx
import pytest
import pytest_asyncio

from pgmcp.ag_graph import AgGraph
from pgmcp.apache_age import ApacheAGE
from pgmcp.db import AgtypeRecord
from pgmcp.environment import Environment, set_current_env
from pgmcp.settings import get_settings

from .setup.database import setup_database
from .setup.sqlalchemy import close_sqlalchemy_engine


# ===========================================================================================
# ENV AND SETTINGS
# ===========================================================================================

ENV = set_current_env(Environment.TESTING)
SETTINGS = get_settings()


# ===========================================================================================
# HOOKS
# ===========================================================================================
setup_database()

# # Session: Before
# @pytest.fixture(scope="session", autouse=True)
# def session_setup():
#     global ONCE
#     if ONCE is None:
#         ONCE = True
    
# Function: Around: Async
@pytest_asyncio.fixture(autouse=True, scope="function")
async def around_function_async():
    # nothing before
    
    yield # execution of the test function

    await close_sqlalchemy_engine()


# ===========================================================================================
# FIXTURES
# ===========================================================================================

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



@pytest.fixture
def complex_content():
    return dedent("""
    As with all SQLAlchemy dialects, all UPPERCASE types that are known to be
    valid with PostgreSQL are importable from the top level dialect, whether
    they originate from `sqlalchemy.types` or from the local dialect:  
    ```
    from sqlalchemy.dialects.postgresql import \
    ARRAY, BIGINT, BIT, BOOLEAN, BYTEA, CHAR, CIDR, DATE, \
    DOUBLE_PRECISION, ENUM, FLOAT, HSTORE, INET, INTEGER, \
    INTERVAL, JSON, JSONB, MACADDR, MONEY, NUMERIC, OID, REAL, SMALLINT, TEXT, \
    TIME, TIMESTAMP, UUID, VARCHAR, INT4RANGE, INT8RANGE, NUMRANGE, \
    DATERANGE, TSRANGE, TSTZRANGE, TSVECTOR
    ```  
    Types which are specific to PostgreSQL, or have PostgreSQL&#45;specific
    construction arguments, are as follows:  
    | Object Name | Description |
    | --- | --- |
    | aggregate_order_by | Represent a PostgreSQL aggregate order by expression. |
    | All(other, arrexpr[, operator]) | A synonym for the `Comparator.all()` method. |
    | Any(other, arrexpr[, operator]) | A synonym for the `Comparator.any()` method. |
    | array | A PostgreSQL ARRAY literal. |
    | ARRAY | PostgreSQL ARRAY type. |
    | array_agg(\*arg, \*\*kw) | PostgreSQL-specific form of `array_agg`, ensures return type is `ARRAY` and not the plain `ARRAY`, unless an explicit `type_` is passed. |
    | BIT |  |
    | BYTEA |  |
    | CIDR |  |
    | DOUBLE_PRECISION |  |
    | ENUM | PostgreSQL ENUM type. |
    | HSTORE | Represent the PostgreSQL HSTORE type. |
    | hstore | Construct an hstore value within a SQL expression using the PostgreSQL `hstore()` function. |
    | INET |  |
    | INTERVAL | PostgreSQL INTERVAL type. |
    | JSON | Represent the PostgreSQL JSON type. |
    | JSONB | Represent the PostgreSQL JSONB type. |
    | MACADDR |  |
    | MONEY | Provide the PostgreSQL MONEY type. |
    | OID | Provide the PostgreSQL OID type. |
    | REAL | The SQL REAL type. |
    | REGCLASS | Provide the PostgreSQL REGCLASS type. |
    | TSVECTOR | The `TSVECTOR` type implements the PostgreSQL text search type TSVECTOR. |
    | UUID | PostgreSQL UUID type. |  
    - *class* sqlalchemy.dialects.postgresql.aggregate_order_by(*target*, *\*order_by*)¶
    - Represent a PostgreSQL aggregate order by expression.  
    E.g.:  
    ```
    from sqlalchemy.dialects.postgresql import aggregate_order_by
    expr = func.array_agg(aggregate_order_by(table.c.a, table.c.b.desc()))
    stmt = ([expr])
    ```  
    would represent the expression:  
    Similarly:  
    ```
    expr = func.string_agg(
    table.c.a,
    aggregate_order_by(literal_column("','"), table.c.a)
    )
    stmt = ([expr])
    ```  
    Would represent:  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.aggregate_order_by` (`sqlalchemy.sql.expression.ColumnElement`)  
    - *class* sqlalchemy.dialects.postgresql.array(*clauses*, *\*\*kw*)¶
    - A PostgreSQL ARRAY literal.  
    This is used to produce ARRAY literals in SQL expressions, e.g.:  
    ```
    from sqlalchemy.dialects.postgresql import array
    from sqlalchemy.dialects import postgresql
    from sqlalchemy import , func

    stmt = ([
    array([1,2]) + array([3,4,5])
    ])

    print(stmt.compile(dialect=postgresql.dialect()))
    ```  
    Produces the SQL:  
    An instance of `array` will always have the datatype
    `ARRAY`. The “inner” type of the array is inferred from
    the values present, unless the `type_` keyword argument is passed:  
    ```
    array(['foo', 'bar'], type_=CHAR)
    ```  
    Multidimensional arrays are produced by nesting `array` constructs.
    The dimensionality of the final `ARRAY`
    type is calculated by
    recursively adding the dimensions of the inner `ARRAY`
    type:  
    ```
    stmt = ([
    array([
    array([1, 2]), array([3, 4]), array([column('q'), column('x')])
    ])
    ])
    print(stmt.compile(dialect=postgresql.dialect()))
    ```  
    Produces:  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.array` (`sqlalchemy.sql.expression.Tuple`)  
    - *class* sqlalchemy.dialects.postgresql.ARRAY(*item_type*, *as_tuple=False*, *dimensions=*, *zero_indexes=False*)¶
    - PostgreSQL ARRAY type.  
    The `ARRAY` type is constructed in the same way
    as the core `ARRAY` type; a member type is required, and a
    number of dimensions is recommended if the type is to be used for more
    than one dimension:  
    ```
    from sqlalchemy.dialects import postgresql

    mytable = Table("mytable", metadata,
    Column("data", postgresql.ARRAY(Integer, dimensions=2))
    )
    ```  
    The `ARRAY` type provides all operations defined on the
    core `ARRAY` type, including support for “dimensions”,
    indexed access, and simple matching such as
    `Comparator.any()` and
    `Comparator.all()`. `ARRAY`
    class also
    provides PostgreSQL-specific methods for containment operations, including
    `Comparator.contains()`
    `Comparator.contained_by()`, and
    `Comparator.overlap()`, e.g.:  
    ```
    mytable.c.data.contains([1, 2])
    ```  
    The `ARRAY` type may not be supported on all
    PostgreSQL DBAPIs; it is currently known to work on psycopg2 only.  
    Additionally, the `ARRAY`
    type does not work directly in
    conjunction with the `ENUM` type. For a workaround, see the
    special type at Using ENUM with ARRAY.  
    See also  
    `ARRAY` - base array type  
    `array` - produces a literal array value.  
    **Members**  
    contained_by(), contains(), overlap(), __init__()  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.ARRAY` (`sqlalchemy.types.ARRAY`)  
    - *class* Comparator(*expr*)¶
    - Define comparison operations for `ARRAY`.  
    Note that these operations are in addition to those provided
    by the base `Comparator` class, including
    `Comparator.any()` and
    `Comparator.all()`.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.ARRAY.Comparator` (`sqlalchemy.types.Comparator`)  
    - *method* `sqlalchemy.dialects.postgresql.ARRAY.Comparator.`contained_by(*other*)¶
    - Boolean expression. Test if elements are a proper subset of the
    elements of the argument array expression.  
    - *method* `sqlalchemy.dialects.postgresql.ARRAY.Comparator.`contains(*other*, *\*\*kwargs*)¶
    - Boolean expression. Test if elements are a superset of the
    elements of the argument array expression.  
    - *method* `sqlalchemy.dialects.postgresql.ARRAY.Comparator.`overlap(*other*)¶
    - Boolean expression. Test if array has elements in common with
    an argument array expression.  
    - *method* `sqlalchemy.dialects.postgresql.ARRAY.`__init__(*item_type*, *as_tuple=False*, *dimensions=*, *zero_indexes=False*)¶
    - Construct an ARRAY.  
    E.g.:  
    ```
    Column('myarray', ARRAY(Integer))
    ```  
    Arguments are:  
    - Parameters:
    - - **item_type**¶ – The data type of items of this array. Note that
    dimensionality is irrelevant here, so multi-dimensional arrays like
    `INTEGER[][]`, are constructed as `ARRAY(Integer)`, not as
    `ARRAY(ARRAY(Integer))` or such.
    - **as_tuple=False**¶ – Specify whether return results
    should be converted to tuples from lists. DBAPIs such
    as psycopg2 return lists by default. When tuples are
    returned, the results are hashable.
    - **dimensions**¶ – if non-None, the ARRAY will assume a fixed
    number of dimensions. This will cause the DDL emitted for this
    ARRAY to include the exact number of bracket clauses `[]`,
    and will also optimize the performance of the type overall.
    Note that PG arrays are always implicitly “non-dimensioned”,
    meaning they can store any number of dimensions no matter how
    they were declared.
    - **zero_indexes=False**¶ –  
    when True, index values will be converted
    between Python zero&#45;based and PostgreSQL one&#45;based indexes, e.g.
    a value of one will be added to all index values before passing
    to the database.  
    - *function* sqlalchemy.dialects.postgresql.array_agg(*\*arg*, *\*\*kw*)¶
    - PostgreSQL-specific form of `array_agg`, ensures
    return type is `ARRAY` and not
    the plain `ARRAY`, unless an explicit `type_`
    is passed.  
    - *function* sqlalchemy.dialects.postgresql.Any(*other*, *arrexpr*, *operator=<built&#45;in function eq>*)¶
    - A synonym for the `Comparator.any()` method.  
    This method is legacy and is here for backwards&#45;compatibility.  
    - *function* sqlalchemy.dialects.postgresql.All(*other*, *arrexpr*, *operator=<built&#45;in function eq>*)¶
    - A synonym for the `Comparator.all()` method.  
    This method is legacy and is here for backwards&#45;compatibility.  
    - *class* sqlalchemy.dialects.postgresql.BIT(*length=*, *varying=False*)¶
    - **Class signature**  
    class `sqlalchemy.dialects.postgresql.BIT` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.BYTEA(*length=*)¶
    - **Class signature**  
    class `sqlalchemy.dialects.postgresql.BYTEA` (`sqlalchemy.types.LargeBinary`)  
    - *method* `sqlalchemy.dialects.postgresql.BYTEA.`__init__(*length=*)¶
    - *inherited from the* `sqlalchemy.types.LargeBinary.__init__` *method of* `LargeBinary`  
    Construct a LargeBinary type.  
    - Parameters:
    - **length**¶ – optional, a length for the column for use in
    DDL statements, for those binary types that accept a length,
    such as the MySQL BLOB type.  
    - *class* sqlalchemy.dialects.postgresql.CIDR¶
    - **Class signature**  
    class `sqlalchemy.dialects.postgresql.CIDR` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.DOUBLE_PRECISION(*precision=*, *asdecimal=False*, *decimal_return_scale=*)¶
    - **Class signature**  
    class `sqlalchemy.dialects.postgresql.DOUBLE_PRECISION` (`sqlalchemy.types.Float`)  
    - *method* `sqlalchemy.dialects.postgresql.DOUBLE_PRECISION.`__init__(*precision=*, *asdecimal=False*, *decimal_return_scale=*)¶
    - *inherited from the* `sqlalchemy.types.Float.__init__` *method of* `Float`  
    Construct a Float.  
    - Parameters:
    - - **precision**¶ – the numeric precision for use in DDL `CREATE
    TABLE`.
    - **asdecimal**¶ – the same flag as that of `Numeric`, but
    defaults to `False`. Note that setting this flag to `True`
    results in floating point conversion.
    - **decimal_return_scale**¶ –  
    Default scale to use when converting
    from floats to Python decimals. Floating point values will typically
    be much longer due to decimal inaccuracy, and most floating point
    database types don’t have a notion of “scale”, so by default the
    float type looks for the first ten decimal places when converting.
    Specifying this value will override that length. Note that the
    MySQL float types, which do include “scale”, will use “scale”
    as the default for decimal_return_scale, if not otherwise specified.  
    - *class* sqlalchemy.dialects.postgresql.ENUM(*\*enums*, *\*\*kw*)¶
    - PostgreSQL ENUM type.  
    This is a subclass of `Enum` which includes
    support for PG’s `CREATE TYPE` and `DROP TYPE`.  
    When the builtin type `Enum` is used and the
    `Enum.native_enum` flag is left at its default of
    True, the PostgreSQL backend will use a `ENUM`
    type as the implementation, so the special create/drop rules
    will be used.  
    The create/drop behavior of ENUM is necessarily intricate, due to the
    awkward relationship the ENUM type has in relationship to the
    parent table, in that it may be “owned” by just a single table, or
    may be shared among many tables.  
    When using `Enum` or `ENUM`
    in an “inline” fashion, the `CREATE TYPE` and `DROP TYPE` is emitted
    corresponding to when the `Table.create()` and
    `Table.drop()`
    methods are called:  
    ```
    table = Table('sometable', metadata,
    Column('some_enum', ENUM('a', 'b', 'c', name='myenum'))
    )

    table.(engine)  # will emit CREATE ENUM and CREATE TABLE
    table.drop(engine)  # will emit DROP TABLE and DROP ENUM
    ```  
    To use a common enumerated type between multiple tables, the best
    practice is to declare the `Enum` or
    `ENUM` independently, and associate it with the
    `MetaData` object itself:  
    ```
    my_enum = ENUM('a', 'b', 'c', name='myenum', metadata=metadata)

    t1 = Table('sometable_one', metadata,
    Column('some_enum', myenum)
    )

    t2 = Table('sometable_two', metadata,
    Column('some_enum', myenum)
    )
    ```  
    When this pattern is used, care must still be taken at the level
    of individual table creates. Emitting CREATE TABLE without also
    specifying `checkfirst=True` will still cause issues:  
    ```
    t1.(engine) # will fail: no such type 'myenum'
    ```  
    If we specify `checkfirst=True`, the individual table-level create
    operation will check for the `ENUM` and create if not exists:  
    ```
    # will check if enum exists, and emit CREATE TYPE if not
    t1.(engine, checkfirst=True)
    ```  
    When using a metadata&#45;level ENUM type, the type will always be created
    and dropped if either the metadata&#45;wide create/drop is called:  
    ```
    metadata.(engine)  # will emit CREATE TYPE
    metadata.drop_all(engine)  # will emit DROP TYPE
    ```  
    The type can also be created and dropped directly:  
    ```
    my_enum.(engine)
    my_enum.drop(engine)
    ```  
    The PostgreSQL `ENUM` type
    now behaves more strictly with regards to CREATE/DROP. A metadata-level
    ENUM type will only be created and dropped at the metadata level,
    not the table level, with the exception of
    `table.create(checkfirst=True)`.
    The `table.drop()` call will now emit a DROP TYPE for a table-level
    enumerated type.  
    **Members**  
    __init__(), create(), drop()  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.ENUM` (`sqlalchemy.types.NativeForEmulated`, `sqlalchemy.types.Enum`)  
    - *method* `sqlalchemy.dialects.postgresql.ENUM.`__init__(*\*enums*, *\*\*kw*)¶
    - Construct an `ENUM`.  
    Arguments are the same as that of
    `Enum`, but also including
    the following parameters.  
    - Parameters:
    - **create_type**¶ – Defaults to True.
    Indicates that `CREATE TYPE` should be
    emitted, after optionally checking for the
    presence of the type, when the parent
    table is being created; and additionally
    that `DROP TYPE` is called when the table
    is dropped. When `False`, no check
    will be performed and no `CREATE TYPE`
    or `DROP TYPE` is emitted, unless
    `ENUM.create()`
    or `ENUM.drop()`
    are called directly.
    Setting to `False` is helpful
    when invoking a creation scheme to a SQL file
    without access to the actual database -
    the `ENUM.create()` and
    `ENUM.drop()` methods can
    be used to emit SQL to a target bind.  
    - *method* `sqlalchemy.dialects.postgresql.ENUM.`(*bind=*, *checkfirst=True*)¶
    - Emit `CREATE TYPE` for this
    `ENUM`.  
    If the underlying dialect does not support
    PostgreSQL CREATE TYPE, no action is taken.  
    - Parameters:
    - - **bind**¶ – a connectable `Engine`,
    `Connection`, or similar object to emit
    SQL.
    - **checkfirst**¶ – if `True`, a query against
    the PG catalog will be first performed to see
    if the type does not exist already before
    creating.  
    - *method* `sqlalchemy.dialects.postgresql.ENUM.`drop(*bind=*, *checkfirst=True*)¶
    - Emit `DROP TYPE` for this
    `ENUM`.  
    If the underlying dialect does not support
    PostgreSQL DROP TYPE, no action is taken.  
    - Parameters:
    - - **bind**¶ – a connectable `Engine`,
    `Connection`, or similar object to emit
    SQL.
    - **checkfirst**¶ – if `True`, a query against
    the PG catalog will be first performed to see
    if the type actually exists before dropping.  
    - *class* sqlalchemy.dialects.postgresql.HSTORE(*text_type=*)¶
    - Represent the PostgreSQL HSTORE type.  
    The `HSTORE` type stores dictionaries containing strings, e.g.:  
    ```
    data_table = Table('data_table', metadata,
    Column('id', Integer, primary_key=True),
    Column('data', HSTORE)
    )

    with engine.connect() as conn:
    conn.execute(
    data_table.insert(),
    data = {"key1": "value1", "key2": "value2"}
    )
    ```  
    `HSTORE` provides for a wide range of operations, including:  
    - Index operations:  
    ```
    data_table.c.data['some key'] == 'some value'
    ```
    - Containment operations:  
    ```
    data_table.c.data.has_key('some key')

    data_table.c.data.has_all(['one', 'two', 'three'])
    ```
    - Concatenation:  
    ```
    data_table.c.data + {"k1": "v1"}
    ```  
    For a full list of special methods see
    `comparator_factory`.  
    For usage with the SQLAlchemy ORM, it may be desirable to combine
    the usage of `HSTORE` with `MutableDict` dictionary
    now part of the `sqlalchemy.ext.mutable`
    extension. This extension will allow “in-place” changes to the
    dictionary, e.g. addition of new keys or replacement/removal of existing
    keys to/from the current dictionary, to produce events which will be
    detected by the unit of work:  
    ```
    from sqlalchemy.ext.mutable import MutableDict

    class MyClass(Base):
    __tablename__ = 'data_table'

    id = Column(Integer, primary_key=True)
    data = Column(MutableDict.as_mutable(HSTORE))

    my_object = session.query(MyClass).one()

    # in&#45;place mutation, requires Mutable extension
    # in order for the ORM to detect
    my_object.data['some_key'] = 'some value'

    session.commit()
    ```  
    When the `sqlalchemy.ext.mutable` extension is not used, the ORM
    will not be alerted to any changes to the contents of an existing
    dictionary, unless that dictionary value is re-assigned to the
    HSTORE-attribute itself, thus generating a change event.  
    See also  
    `hstore` - render the PostgreSQL `hstore()` function.  
    **Members**  
    array(), contained_by(), contains(), defined(), delete(), has_all(), has_any(), has_key(), keys(), matrix(), slice(), vals(), __init__(), bind_processor(), comparator_factory, hashable, result_processor()  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.HSTORE` (`sqlalchemy.types.Indexable`, `sqlalchemy.types.Concatenable`, `sqlalchemy.types.TypeEngine`)  
    - *class* Comparator(*expr*)¶
    - Define comparison operations for `HSTORE`.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.HSTORE.Comparator` (`sqlalchemy.types.Comparator`, `sqlalchemy.types.Comparator`)  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`array()¶
    - Text array expression. Returns array of alternating keys and
    values.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`contained_by(*other*)¶
    - Boolean expression. Test if keys are a proper subset of the
    keys of the argument jsonb expression.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`contains(*other*, *\*\*kwargs*)¶
    - Boolean expression. Test if keys (or array) are a superset
    of/contained the keys of the argument jsonb expression.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`defined(*key*)¶
    - Boolean expression. Test for presence of a non&#45;NULL value for
    the key. Note that the key may be a SQLA expression.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`(*key*)¶
    - HStore expression. Returns the contents of this hstore with the
    given key deleted. Note that the key may be a SQLA expression.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`has_all(*other*)¶
    - Boolean expression. Test for presence of all keys in jsonb  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`has_any(*other*)¶
    - Boolean expression. Test for presence of any key in jsonb  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`has_key(*other*)¶
    - Boolean expression. Test for presence of a key. Note that the
    key may be a SQLA expression.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`keys()¶
    - Text array expression. Returns array of keys.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`matrix()¶
    - Text array expression. Returns array of [key, value] pairs.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`slice(*array*)¶
    - HStore expression. Returns a subset of an hstore defined by
    array of keys.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.Comparator.`vals()¶
    - Text array expression. Returns array of values.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.`__init__(*text_type=*)¶
    - Construct a new `HSTORE`.  
    - Parameters:
    - **text_type**¶ –  
    the type that should be used for indexed values.
    Defaults to `Text`.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.`bind_processor(*dialect*)¶
    - Return a conversion function for processing bind values.  
    Returns a callable which will receive a bind parameter value
    as the sole positional argument and will return a value
    to send to the DB&#45;API.  
    If processing is not necessary, the method should return `None`.  
    - Parameters:
    - **dialect**¶ – Dialect instance in use.  
    - *attribute* `sqlalchemy.dialects.postgresql.HSTORE.`comparator_factory¶
    - alias of `Comparator`  
    - *attribute* `sqlalchemy.dialects.postgresql.HSTORE.`hashable *= False*¶
    - Flag, if False, means values from this type aren’t hashable.  
    Used by the ORM when uniquing result lists.  
    - *method* `sqlalchemy.dialects.postgresql.HSTORE.`result_processor(*dialect*, *coltype*)¶
    - Return a conversion function for processing result row values.  
    Returns a callable which will receive a result row column
    value as the sole positional argument and will return a value
    to return to the user.  
    If processing is not necessary, the method should return `None`.  
    - Parameters:  
    - *class* sqlalchemy.dialects.postgresql.hstore(*\*args*, *\*\*kwargs*)¶
    - Construct an hstore value within a SQL expression using the
    PostgreSQL `hstore()` function.  
    The `hstore` function accepts one or two arguments as described
    in the PostgreSQL documentation.  
    E.g.:  
    ```
    from sqlalchemy.dialects.postgresql import array, hstore

    ([hstore('key1', 'value1')])

    ([
    hstore(
    array(['key1', 'key2', 'key3']),
    array(['value1', 'value2', 'value3'])
    )
    ])
    ```  
    See also  
    `HSTORE` - the PostgreSQL `HSTORE` datatype.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.hstore` (`sqlalchemy.sql.functions.GenericFunction`)  
    - *attribute* `sqlalchemy.dialects.postgresql.hstore.`type¶
    - alias of `HSTORE`  
    - *class* sqlalchemy.dialects.postgresql.INET¶
    - **Class signature**  
    class `sqlalchemy.dialects.postgresql.INET` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.INTERVAL(*precision=*, *fields=*)¶
    - PostgreSQL INTERVAL type.  
    The INTERVAL type may not be supported on all DBAPIs.
    It is known to work on psycopg2 and not pg8000 or zxjdbc.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.INTERVAL` (`sqlalchemy.types.NativeForEmulated`, `sqlalchemy.types._AbstractInterval`)  
    - *method* `sqlalchemy.dialects.postgresql.INTERVAL.`__init__(*precision=*, *fields=*)¶
    - Construct an INTERVAL.  
    - Parameters:
    - - **precision**¶ – optional integer precision value
    - **fields**¶ –  
    string fields specifier. allows storage of fields
    to be limited, such as `"YEAR"`, `"MONTH"`, `"DAY TO HOUR"`,
    etc.  
    - *class* sqlalchemy.dialects.postgresql.JSON(*=False*, *astext_type=*)¶
    - Represent the PostgreSQL JSON type.  
    This type is a specialization of the Core-level `JSON`
    type. Be sure to read the documentation for `JSON` for
    important tips regarding treatment of NULL values and ORM use.  
    The operators provided by the PostgreSQL version of `JSON`
    include:  
    - Index operations (the `&#45;>` operator):  
    ```
    data_table.c.data['some key']

    data_table.c.data[5]
    ```
    - Index operations returning text (the `&#45;>>` operator):  
    ```
    data_table.c.data['some key'].astext == 'some value'
    ```  
    Note that equivalent functionality is available via the
    `Comparator.as_string` accessor.
    - Index operations with CAST
    (equivalent to `CAST(col &#45;>> ['some key'] AS <type>)`):  
    ```
    data_table.c.data['some key'].astext.cast(Integer) == 5
    ```  
    Note that equivalent functionality is available via the
    `Comparator.as_integer` and similar accessors.
    - Path index operations (the `#>` operator):  
    ```
    data_table.c.data[('key_1', 'key_2', 5, ..., 'key_n')]
    ```
    - Path index operations returning text (the `#>>` operator):  
    ```
    data_table.c.data[('key_1', 'key_2', 5, ..., 'key_n')].astext == 'some value'
    ```  
    The `ColumnElement.cast()`
    operator on
    JSON objects now requires that the `Comparator.astext`
    modifier be called explicitly, if the cast works only from a textual
    string.  
    Index operations return an expression object whose type defaults to
    `JSON` by default,
    so that further JSON-oriented instructions
    may be called upon the result type.  
    Custom serializers and deserializers are specified at the dialect level,
    that is using `create_engine()`. The reason for this is that when
    using psycopg2, the DBAPI only allows serializers at the per-cursor
    or per-connection level. E.g.:  
    ```
    engine = ("postgresql://scott:tiger@localhost/test",
    json_serializer=my_serialize_fn,
    json_deserializer=my_deserialize_fn
    )
    ```  
    When using the psycopg2 dialect, the json_deserializer is registered
    against the database using `psycopg2.extras.register_default_json`.  
    See also  
    `JSON` - Core level JSON type  
    `JSONB`  
    **Members**  
    astext, __init__(), comparator_factory  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.JSON` (`sqlalchemy.types.JSON`)  
    - *class* Comparator(*expr*)¶
    - Define comparison operations for `JSON`.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.JSON.Comparator` (`sqlalchemy.types.Comparator`)  
    - *attribute* `sqlalchemy.dialects.postgresql.JSON.Comparator.`astext¶
    - On an indexed expression, use the “astext” (e.g. “&#45;>>”)
    conversion when rendered in SQL.  
    E.g.:  
    See also  
    `ColumnElement.cast()`  
    - *method* `sqlalchemy.dialects.postgresql.JSON.`__init__(*=False*, *astext_type=*)¶
    - Construct a `JSON` type.  
    - Parameters:
    - - **none_as_null**¶ –  
    if True, persist the value `None` as a
    SQL NULL value, not the JSON encoding of `null`. Note that
    when this flag is False, the `null()` construct can still
    be used to persist a NULL value:  
    ```
    from sqlalchemy import null
    conn.execute(table.insert(), data=null())
    ```
    - **astext_type**¶ –  
    the type to use for the
    `Comparator.astext`
    accessor on indexed attributes. Defaults to `Text`.  
    - *attribute* `sqlalchemy.dialects.postgresql.JSON.`comparator_factory¶
    - alias of `Comparator`  
    - *class* sqlalchemy.dialects.postgresql.JSONB(*=False*, *astext_type=*)¶
    - Represent the PostgreSQL JSONB type.  
    The `JSONB` type stores arbitrary JSONB format data,
    e.g.:  
    ```
    data_table = Table('data_table', metadata,
    Column('id', Integer, primary_key=True),
    Column('data', JSONB)
    )

    with engine.connect() as conn:
    conn.execute(
    data_table.insert(),
    data = {"key1": "value1", "key2": "value2"}
    )
    ```  
    The `JSONB` type includes all operations provided by
    `JSON`, including the same behaviors for indexing
    operations.
    It also adds additional operators specific to JSONB, including
    `Comparator.has_key()`, `Comparator.has_all()`,
    `Comparator.has_any()`, `Comparator.contains()`,
    and `Comparator.contained_by()`.  
    Like the `JSON` type, the `JSONB`
    type does not detect
    in-place changes when used with the ORM, unless the
    `sqlalchemy.ext.mutable` extension is used.  
    Custom serializers and deserializers
    are shared with the `JSON` class,
    using the `json_serializer`
    and `json_deserializer` keyword arguments. These must be specified
    at the dialect level using `create_engine()`. When using
    psycopg2, the serializers are associated with the jsonb type using
    `psycopg2.extras.register_default_jsonb` on a per-connection basis,
    in the same way that `psycopg2.extras.register_default_json` is used
    to register these handlers with the json type.  
    **Members**  
    contained_by(), contains(), has_all(), has_any(), has_key(), comparator_factory  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.JSONB` (`sqlalchemy.dialects.postgresql.json.JSON`)  
    - *class* Comparator(*expr*)¶
    - Define comparison operations for `JSON`.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.JSONB.Comparator` (`sqlalchemy.dialects.postgresql.json.Comparator`)  
    - *method* `sqlalchemy.dialects.postgresql.JSONB.Comparator.`contained_by(*other*)¶
    - Boolean expression. Test if keys are a proper subset of the
    keys of the argument jsonb expression.  
    - *method* `sqlalchemy.dialects.postgresql.JSONB.Comparator.`contains(*other*, *\*\*kwargs*)¶
    - Boolean expression. Test if keys (or array) are a superset
    of/contained the keys of the argument jsonb expression.  
    - *method* `sqlalchemy.dialects.postgresql.JSONB.Comparator.`has_all(*other*)¶
    - Boolean expression. Test for presence of all keys in jsonb  
    - *method* `sqlalchemy.dialects.postgresql.JSONB.Comparator.`has_any(*other*)¶
    - Boolean expression. Test for presence of any key in jsonb  
    - *method* `sqlalchemy.dialects.postgresql.JSONB.Comparator.`has_key(*other*)¶
    - Boolean expression. Test for presence of a key. Note that the
    key may be a SQLA expression.  
    - *attribute* `sqlalchemy.dialects.postgresql.JSONB.`comparator_factory¶
    - alias of `Comparator`  
    - *class* sqlalchemy.dialects.postgresql.MACADDR¶
    - **Class signature**  
    class `sqlalchemy.dialects.postgresql.MACADDR` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.MONEY¶
    - Provide the PostgreSQL MONEY type.  
    Depending on driver, result rows using this type may return a
    string value which includes currency symbols.  
    For this reason, it may be preferable to provide conversion to a
    numerically-based currency datatype using `TypeDecorator`:  
    ```
    import re
    import decimal
    from sqlalchemy import TypeDecorator

    class NumericMoney(TypeDecorator):
    impl = MONEY

    def process_result_value(self, value: Any, dialect: Any) &#45;> :
    if value is  :
    # adjust this for the currency and numeric
    m = re.match(r"\$([\d.]+)", value)
    if m:
    value = decimal.Decimal(m.group(1))
    return value
    ```  
    Alternatively, the conversion may be applied as a CAST using
    the `TypeDecorator.column_expression()` method as follows:  
    ```
    import decimal
    from sqlalchemy import cast
    from sqlalchemy import TypeDecorator

    class NumericMoney(TypeDecorator):
    impl = MONEY

    def column_expression(self, column: Any):
    return cast(column, Numeric())
    ```  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.MONEY` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.OID¶
    - Provide the PostgreSQL OID type.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.OID` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.REAL(*precision=*, *asdecimal=False*, *decimal_return_scale=*)¶
    - The SQL REAL type.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.REAL` (`sqlalchemy.types.Float`)  
    - *method* `sqlalchemy.dialects.postgresql.REAL.`__init__(*precision=*, *asdecimal=False*, *decimal_return_scale=*)¶
    - *inherited from the* `sqlalchemy.types.Float.__init__` *method of* `Float`  
    Construct a Float.  
    - Parameters:
    - - **precision**¶ – the numeric precision for use in DDL `CREATE
    TABLE`.
    - **asdecimal**¶ – the same flag as that of `Numeric`, but
    defaults to `False`. Note that setting this flag to `True`
    results in floating point conversion.
    - **decimal_return_scale**¶ –  
    Default scale to use when converting
    from floats to Python decimals. Floating point values will typically
    be much longer due to decimal inaccuracy, and most floating point
    database types don’t have a notion of “scale”, so by default the
    float type looks for the first ten decimal places when converting.
    Specifying this value will override that length. Note that the
    MySQL float types, which do include “scale”, will use “scale”
    as the default for decimal_return_scale, if not otherwise specified.  
    - *class* sqlalchemy.dialects.postgresql.REGCLASS¶
    - Provide the PostgreSQL REGCLASS type.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.REGCLASS` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.TSVECTOR¶
    - The `TSVECTOR` type implements the PostgreSQL
    text search type TSVECTOR.  
    It can be used to do full text queries on natural language
    documents.  
    See also  
    Full Text Search  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.TSVECTOR` (`sqlalchemy.types.TypeEngine`)  
    - *class* sqlalchemy.dialects.postgresql.UUID(*as_uuid=False*)¶
    - PostgreSQL UUID type.  
    Represents the UUID column type, interpreting
    data either as natively returned by the DBAPI
    or as Python uuid objects.  
    The UUID type may not be supported on all DBAPIs.
    It is known to work on psycopg2 and not pg8000.  
    **Class signature**  
    class `sqlalchemy.dialects.postgresql.UUID` (`sqlalchemy.types.TypeEngine`)  
    - *method* `sqlalchemy.dialects.postgresql.UUID.`__init__(*as_uuid=False*)¶
    - Construct a UUID type.  
    - Parameters:
    - **as_uuid=False**¶ – if True, values will be interpreted
    as Python uuid objects, converting to/from string via the
    DBAPI.
    """)
