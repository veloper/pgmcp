from __future__ import annotations

import json

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, List, Self, TypeVar, Union, overload

import networkx as nx

from pydantic import (BaseModel, ConfigDict, Field, PrivateAttr, field_serializer, field_validator, model_serializer,
                      model_validator)
from typing_extensions import _SpecialForm

from pgmcp.ag_edges import AgEdges
from pgmcp.ag_query_builder import AgQueryBuilderEdge, AgQueryBuilderVertex
from pgmcp.ag_vertices import AgVertices
from pgmcp.lru_cache import LRUCache
from pgmcp.royal_description import RoyalDescription
from pgmcp.utils import deep_merge


if TYPE_CHECKING:
    from pgmcp.ag_edge import AgEdge
    from pgmcp.ag_vertex import AgVertex
    from pgmcp.db import AgtypeRecord


class AgGraph(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    name        : str
    vertices    : AgVertices = Field(default_factory=lambda: AgVertices(root=[]))
    edges       : AgEdges = Field(default_factory=lambda: AgEdges(root=[]))

    # ===================================================================
    # Model Serializer
    # ===================================================================
    @model_serializer
    def custom_serializer(self) -> dict:
        """Custom serializer to handle the serialization of the model."""
        return {
            "name": self.name,
            "vertices": self.vertices,
            "edges": self.edges
        }

    # ===================================================================
    # Private Attributes
    # ===================================================================
    
    _vertices_query_cache: LRUCache[int, List[AgVertex]] = PrivateAttr(default_factory=lambda: LRUCache(max_size=100))
    _edges_query_cache: LRUCache[int, List[AgEdge]] = PrivateAttr(default_factory=lambda: LRUCache(max_size=100))

    def _clear_query_cache(self) -> None:
        """Clear the query caches for vertices and edges."""
        self._vertices_query_cache.clear()
        self._edges_query_cache.clear()
        
    # ===================================================================
    # Validators
    # - These type of validators exist all the way down to pass the graph
    # ===================================================================

    
    @model_validator(mode="after")
    def ensure_vertices_have_graph(self) -> Self:
        self.vertices.graph = self
        for vertex in self.vertices:
            vertex.graph = self
        return self

    @model_validator(mode="after")
    def ensure_edges_have_graph(self) -> Self:
        self.edges.graph = self
        for edge in self.edges:
            edge.graph = self
        return self

    # ===================================================================
    # Helpers
    # ====================================================================
    
    @staticmethod
    def generate_ident() -> str:
        """Generate a new unique identifier for a vertex or edge.
        
        It will take the form of the RoyalDescription with 3 words (last
        being a noun) separated by the "§" delimiter to help prevent
        llms/ais from stemming, ngramming, or otherwise messing-up a unit
        of meaning.
        """
        return RoyalDescription.generate(words=3, delimiter="§")

    # ===================================================================
    # Mutation Methods
    # ===================================================================

    def add_vertices(self, vertices: List[AgVertex]) -> None:
        for vertex in vertices:
            self.add_vertex(vertex)

    def add_edges(self, edges: List[AgEdge]) -> None:
        for edge in edges:
            self.add_edge(edge)

        
    @overload # Pass required + optional kwargs
    def add_vertex(self, label: str, ident: str, *, properties: Dict[str, Any] = {}, id : int | None = None) -> AgVertex: ...
    @overload # Pass obj
    def add_vertex(self, vertex: AgVertex) -> AgVertex: ...
    @overload # Pass model_validate compatible dict
    def add_vertex(self, vertex: Dict[str, Any]) -> AgVertex: ...
    def add_vertex(self, 
        *args,
        **kwargs
    ) -> AgVertex:
        def resolve_to_instance(*args, **kwargs) -> AgVertex:
            from pgmcp.ag_vertex import AgVertex
            attrs : Dict[str, Any] = {}
            
            # If overload 1: args are label, ident, properties, kwargs include id
            if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], str):
                attrs["label"] = args[0]
                attrs["ident"] = args[1]
                if "properties" in kwargs:
                    attrs["properties"] = kwargs.get("properties", {})
                if "id" in kwargs:
                    attrs["id"] = kwargs.get("id")
                return AgVertex.model_validate(attrs)
            
            # If overload 2: args are a single AgVertex instance
            if len(args) == 1 and isinstance(args[0], AgVertex):
                return args[0]
            
            # If overload 3: args are a dict
            if isinstance(args, tuple) and len(args) > 0 and isinstance(args[0], dict):
                return AgVertex.model_validate(args[0])
                    
            raise TypeError(f"Unrecognized arguments for add_vertex: {args}, {kwargs}")
            

        vertex_instance = resolve_to_instance(*args, **kwargs)
        vertex_instance.graph = self
        vertex_instance.ident = vertex_instance.ident if vertex_instance.has_ident else self.generate_ident()
        self.vertices.append(vertex_instance)
        self._clear_query_cache()
        return vertex_instance

    @overload # Pass required + optional kwargs
    def add_edge(self, label: str, start_ident: str, end_ident: str, *, properties: Dict[str, Any] = {}, ident: str | None = None, id: int | None = None, start_id: int | None = None, end_id: int | None = None) -> AgEdge: ...
    @overload # Pass obj
    def add_edge(self, edge: AgEdge) -> AgEdge: ...
    @overload # Pass model_validate compatible dict
    def add_edge(self, edge: Dict[str, Any]) -> AgEdge: ...
    def add_edge(self,
        *args,
        **kwargs: Any
    ) -> AgEdge:
        def resolve_to_instance(*args, **kwargs) -> AgEdge:
            from pgmcp.ag_edge import AgEdge
            attrs: Dict[str, Any] = {}

            # If overload 1: ARGS + KWARGS
            if len(args) == 3 and isinstance(args[0], str) and isinstance(args[1], str) and isinstance(args[2], str):
                attrs["label"] = args[0]
                attrs["start_ident"] = args[1]
                attrs["end_ident"] = args[2]
                if "properties" in kwargs:
                    attrs["properties"] = kwargs.get("properties", {})
                if "ident" in kwargs:
                    attrs["ident"] = kwargs.get("ident")
                if "id" in kwargs:
                    attrs["id"] = kwargs.get("id")
                if "start_id" in kwargs:
                    attrs["start_id"] = kwargs.get("start_id")
                if "end_id" in kwargs:
                    attrs["end_id"] = kwargs.get("end_id")
                    
                return AgEdge.model_validate(attrs)
            
            # If overload 2: OBJECT
            if len(args) == 1 and isinstance(args[0], AgEdge):
                return args[0]
            
            # If overload 3: DICT
            if isinstance(args, tuple) and len(args) > 0 and isinstance(args[0], dict):
                return AgEdge.model_validate(args[0])
                    
            raise TypeError(f"Unrecognized arguments for add_edge: {args}, {kwargs}")
            

        edge_instance = resolve_to_instance(*args, **kwargs)
        edge_instance.graph = self
        edge_instance.ident = edge_instance.ident if edge_instance.has_ident else self.generate_ident()
        
        if not edge_instance.has_start_ident or not edge_instance.has_end_ident:
            raise ValueError(f"Edge must have both start_ident and end_ident set, for args, kwargs: {args}, {kwargs}")

        self.edges.append(edge_instance)
        self._clear_query_cache()
        return edge_instance
        
    def remove_vertex(self, vertex: AgVertex) -> None:
        if vertex not in self.vertices:
            return # no-op
        self.vertices.remove(vertex)
        self._clear_query_cache()

    def remove_edge(self, edge: AgEdge) -> None:
        if edge not in self.edges:
            return # no-op
        self.edges.remove(edge)
        self._clear_query_cache()
        
    def get_vertex_by_ident(self, ident: str) -> 'AgVertex | None':
        return self.vertices.get_by_ident(ident)

    def get_edge_by_ident(self, ident: str) -> 'AgEdge | None':
        return self.edges.get_by_ident(ident)
    
    
    @overload
    def upsert_vertex(self, label: str, ident: str, *, properties: Dict[str, Any] = {}, id: int | None = None) -> AgVertex: ...
    @overload
    def upsert_vertex(self, vertex: AgVertex) -> AgVertex: ...
    @overload
    def upsert_vertex(self, vertex: Dict[str, Any]) -> AgVertex: ...
    def upsert_vertex(self, *args, **kwargs) -> AgVertex:
        def resolve_to_instance(*args, **kwargs) -> AgVertex:
            from pgmcp.ag_vertex import AgVertex
            attrs: Dict[str, Any] = {}

            if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], str):
                attrs["label"] = args[0]
                attrs["ident"] = args[1]
                if "properties" in kwargs:
                    attrs["properties"] = kwargs.get("properties", {})
                if "id" in kwargs:
                    attrs["id"] = kwargs.get("id")
                return AgVertex.model_validate(attrs)
            if len(args) == 1 and isinstance(args[0], AgVertex):
                return args[0]
            if isinstance(args, tuple) and len(args) > 0 and isinstance(args[0], dict):
                return AgVertex.model_validate(args[0])
            raise TypeError(f"Unrecognized arguments for upsert_vertex: {args}, {kwargs}")

        vertex_instance = resolve_to_instance(*args, **kwargs)
        vertex_instance.graph = self
        vertex_instance.ident = vertex_instance.ident if vertex_instance.has_ident else self.generate_ident()
        
        
        if existing := self.get_vertex_by_ident(vertex_instance.ident):
            # Deep Merge Props
            original_props = dict(existing.properties)
            changed_props = dict(vertex_instance.properties)
            merged_props = deep_merge(original_props, changed_props)
            for key, value in merged_props.items():
                existing.properties[key] = value
                
            existing.label = vertex_instance.label
        else:
            self.vertices.append(vertex_instance)
        self._clear_query_cache()
        return vertex_instance

    @overload
    def upsert_edge(self, label: str, start_ident: str, end_ident: str, *, properties: Dict[str, Any] = {}, ident: str | None = None, id: int | None = None, start_id: int | None = None, end_id: int | None = None) -> AgEdge: ...
    @overload
    def upsert_edge(self, edge: AgEdge) -> AgEdge: ...
    @overload
    def upsert_edge(self, edge: Dict[str, Any]) -> AgEdge: ...
    def upsert_edge(self, *args, **kwargs) -> AgEdge:
        def resolve_to_instance(*args, **kwargs) -> AgEdge:
            from pgmcp.ag_edge import AgEdge
            attrs: Dict[str, Any] = {}

            if len(args) == 3 and all(isinstance(a, str) for a in args[:3]):
                attrs["label"] = args[0]
                attrs["start_ident"] = args[1]
                attrs["end_ident"] = args[2]
                if "properties" in kwargs:
                    attrs["properties"] = kwargs.get("properties", {})
                if "ident" in kwargs:
                    attrs["ident"] = kwargs.get("ident")
                if "id" in kwargs:
                    attrs["id"] = kwargs.get("id")
                if "start_id" in kwargs:
                    attrs["start_id"] = kwargs.get("start_id")
                if "end_id" in kwargs:
                    attrs["end_id"] = kwargs.get("end_id")
                return AgEdge.model_validate(attrs)
            if len(args) == 1 and isinstance(args[0], AgEdge):
                return args[0]
            if isinstance(args, tuple) and len(args) > 0 and isinstance(args[0], dict):
                return AgEdge.model_validate(args[0])
            raise TypeError(f"Unrecognized arguments for upsert_edge: {args}, {kwargs}")

        edge_instance = resolve_to_instance(*args, **kwargs)
        
        edge_instance.graph = self
        edge_instance.ident = edge_instance.ident if edge_instance.has_ident else self.generate_ident()
        if not edge_instance.has_start_ident or not edge_instance.has_end_ident:
            raise ValueError(f"Edge must have both start_ident and end_ident set, for args, kwargs: {args}, {kwargs}")
        
        # If an ident is provided, try to find by ident
        existing = self.get_edge_by_ident(edge_instance.ident)
        
        # Attempt to find an existing edge via start and end identifiers + label (if ident came up empty)
        if not existing:
            existing = self.edges.query().start_ident(edge_instance.start_ident).end_ident(edge_instance.end_ident).label(edge_instance.label).first() # type: ignore

        # if _Still_ not found, then we create a new edge


        if existing:
            # Deep Merge Props
            original_props = dict(existing.properties)
            changed_props = dict(edge_instance.properties)
            merged_props = deep_merge(original_props, changed_props)
            for key, value in merged_props.items():
                existing.properties[key] = value
            
            existing.label = edge_instance.label
        else:
            self.add_edge(edge_instance)
        self._clear_query_cache()
        return edge_instance
    
    
    

    # ===================================================================
    # Type Conversion: Agtype
    # ===================================================================

    @classmethod
    def from_agtype_records(cls, name: str, records: List[AgtypeRecord]) -> Self:
        # Circular import workaround
        from pgmcp.ag_edge import AgEdge
        from pgmcp.ag_vertex import AgVertex

        # Gather
        vertex_type_records: List[AgtypeRecord] = []
        edges_type_records: List[AgtypeRecord] = []
        for record in records:
            if record.is_vertex:
                vertex_type_records.append(record)
            elif record.is_edge:
                edges_type_records.append(record)
        
        # Init Graph
        graph = cls.model_validate({"name": name})
        
        # Vertices
        for record in vertex_type_records:
            
            label = record.label
            properties = record.properties
            ident = str(properties.get("ident"))
            id    = record.id
            graph.add_vertex(label, ident, id=id, properties=properties)
        
        # Edges
        for record in edges_type_records:
            label       = record.label
            properties  = record.properties
            ident       = str(properties.get("ident"))
            start_ident = str(properties.get("start_ident"))
            end_ident   = str(properties.get("end_ident"))
            id          = record.id
            start_id    = record.start_id
            end_id      = record.end_id


            graph.add_edge(label, start_ident, end_ident,
                properties=properties,
                ident=ident,
                id=record.id,
                start_id=start_id,
                end_id=end_id
            )
    
        
        return graph

    def to_agtype_records(self) -> List[AgtypeRecord]:
        records = []
        for vertex in self.vertices:
            records.append(vertex.to_agtype_record())
        for edge in self.edges:
            records.append(edge.to_agtype_record())
        return records

    # ===================================================================
    # Type Conversion: NetworkX
    # ===================================================================

    @classmethod
    def from_networkx(cls, G: nx.MultiDiGraph) -> Self:
        """Convert a NetworkX MultiDiGraph to an AgGraph instance."""
        from pgmcp.ag_edge import AgEdge
        from pgmcp.ag_vertex import AgVertex

        ag_graph = cls.model_validate({"name": G.name or "untitled_graph"}) 
    
        # Vertices
        for node, attrs in G.nodes(data=True):
            ident = str(node)
            vertex_data = dict(attrs)
            # Ensure properties dict exists and has ident
            if "properties" not in vertex_data or not isinstance(vertex_data["properties"], dict):
                vertex_data["properties"] = {}
            if "ident" not in vertex_data["properties"]:
                vertex_data["properties"]["ident"] = ident
            vertex = AgVertex.model_validate(vertex_data)
            vertex.ident = ident  # Ensure the vertex has an identifier
            ag_graph.add_vertex(vertex)

        # Edges
        for u, v, key, attrs in G.edges(keys=True, data=True):
            start_ident = str(u)
            end_ident = str(v)
            edge_data = dict(attrs)
            # Ensure properties dict exists and has ident
            if "properties" not in edge_data or not isinstance(edge_data["properties"], dict):
                edge_data["properties"] = {}
            if "ident" not in edge_data["properties"] or edge_data["properties"]["ident"] in (None, ""):
                edge_data["properties"]["ident"] = str(key) if key else f"{start_ident}-{end_ident}"
            edge = AgEdge.model_validate(edge_data)
            edge.start_ident = start_ident
            edge.end_ident = end_ident
            if key and (edge.ident is None or edge.ident == ""):
                edge.ident = str(key)
            ag_graph.add_edge(edge)

        return ag_graph


    def to_networkx(self) -> nx.MultiDiGraph:
        """Convert the AgGraph instance to a NetworkX MultiDiGraph."""
        G = nx.MultiDiGraph()
        G.name = self.name or "untitled_graph"
        
        for vertex in self.vertices:
            G.add_node(vertex.ident, **vertex.model_dump())
        
        for edge in self.edges:
            G.add_edge(edge.start_ident, edge.end_ident, key=edge.ident, **edge.model_dump())

        return G

    # ===================================================================
    # Type Conversion: JSON
    # ===================================================================

    @classmethod
    def from_json(cls, json_data: str) -> Self:
        data = json.loads(json_data)
        return cls.from_dict(data)
    
    def to_json(self) -> str:
        return self.model_dump_json()

    # ===================================================================
    # Type Conversion: JSON
    # ===================================================================

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        graph = cls.model_validate(data)
        # Set ._graph private attribute directly for all vertices and edges
        for v in graph.vertices:
            object.__setattr__(v, "_graph", graph)
        for e in graph.edges:
            object.__setattr__(e, "_graph", graph)
        graph._clear_query_cache()
        return graph

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def deepcopy(self) -> "AgGraph":
        """Return a deep copy of the graph using model_dump_json and model_validate."""
        json_data = self.model_dump_json()
        return type(self).model_validate_json(json_data)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.model_dump_json() == other.model_dump_json()
    
    
    

# ===================================================================
"""
E   pydantic.errors.PydanticUserError: `AgQueryBuilderVertex` is not 
      fully defined; you should define `AgGraph`, then call 
      `AgQueryBuilderVertex.model_rebuild()`.
E   
E   For further information visit https://errors.pydantic.dev/2.11/u/class-not-fully-defined
""" 
# ===================================================================
AgQueryBuilderVertex.model_rebuild()
AgQueryBuilderEdge.model_rebuild()
