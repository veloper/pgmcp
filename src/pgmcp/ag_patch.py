from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Callable, Dict, List, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pgmcp.ag_edge import AgEdge
from pgmcp.ag_entity import AgEntity
from pgmcp.ag_graph import AgGraph
from pgmcp.ag_mutation import AgMutation
from pgmcp.ag_vertex import AgVertex


class AgPatch(BaseModel):
    """A patch object that contains the minimal set of operations required to transform one graph a into graph b."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    graph_a: AgGraph
    graph_b: AgGraph

    mutations: List[AgMutation] = Field(default_factory=list)

    @classmethod
    def from_a_to_b(cls, graph_a: AgGraph, graph_b: AgGraph) -> Self:
        """Create a patch from graph_a to graph_b."""
        return cls.model_validate({ 'graph_a': graph_a, 'graph_b': graph_b})

    def model_post_init(self, __context=None) -> None:
        """Post-initialization to ensure graphs are set and recalculate mutations."""
        if not isinstance(self.graph_a, AgGraph) or not isinstance(self.graph_b, AgGraph):
            raise TypeError("graph_a and graph_b must be instances of AgGraph.")
        self.recalculate()
    
    def recalculate(self) -> None:
        """Calculate the mutations between graph_a and graph_b
        
        Order matters, mutations must 'run' in the order they are created (FIFO):
        1. Edge removals
        2. Vertex removals
        3. Vertex additions
        4. Vertex updates
        5. Edge additions
        6. Edge updates
        """
        self.mutations = []
        a_vertex_map: dict[str, AgVertex] = {v.ident: v for v in self.graph_a.vertices if v.ident}
        b_vertex_map: dict[str, AgVertex] = {v.ident: v for v in self.graph_b.vertices if v.ident}
        a_edge_map: dict[str, AgEdge] = {e.ident: e for e in self.graph_a.edges if e.ident}
        b_edge_map: dict[str, AgEdge] = {e.ident: e for e in self.graph_b.edges if e.ident}

        # 1. Edge removals (edges in A not in B)
        for ident, e in a_edge_map.items():
            if ident not in b_edge_map and e.ident is not None and e.label is not None:
                self.mutations.append(
                    AgMutation.remove_edge(
                        ident=e.ident,
                        label=e.label,
                        id=e.id,
                        start_id=e.start_id,
                        end_id=e.end_id,
                        start_ident=e.start_ident,
                        end_ident=e.end_ident
                    )
                )

        # 2. Vertex removals (vertices in A not in B)
        for ident, v in a_vertex_map.items():
            if ident not in b_vertex_map and v.ident is not None and v.label is not None:
                self.mutations.append(
                    AgMutation.remove_vertex(
                        ident=v.ident,
                        label=v.label,
                        id=v.id
                    )
                )

        # 3. Vertex additions (vertices in B not in A)
        for ident, v in b_vertex_map.items():
            if ident not in a_vertex_map and v.ident is not None and v.label is not None:
                self.mutations.append(
                    AgMutation.add_vertex(
                        ident=v.ident,
                        label=v.label,
                        properties=v.properties.root.copy(),
                        id=v.id
                    )
                )

        # 4. Vertex updates (vertices in both, but label or properties differ)
        for ident, v in b_vertex_map.items():
            if ident in a_vertex_map:
                a_v = a_vertex_map[ident]
                if v.label != a_v.label or v.properties.root != a_v.properties.root:
                    if v.ident is not None and v.label is not None:
                        self.mutations.append(
                            AgMutation.update_vertex(
                                ident=v.ident,
                                label=v.label,
                                properties=v.properties.root.copy(),
                                id=v.id
                            )
                        )

        # 5. Edge additions (edges in B not in A)
        for ident, e in b_edge_map.items():
            if ident not in a_edge_map:
                if e.start_ident is None:
                    raise ValueError(f"Edge {e.ident} has no start_ident, cannot add.")
                if e.end_ident is None:
                    raise ValueError(f"Edge {e.ident} has no end_ident, cannot add.")
                # Look up start_label and end_label from vertices in graph_b
                start_label = None
                end_label = None
                if e.start_ident in b_vertex_map:
                    start_label = b_vertex_map[e.start_ident].label
                if e.end_ident in b_vertex_map:
                    end_label = b_vertex_map[e.end_ident].label
                self.mutations.append(
                    AgMutation.add_edge(
                        ident=e.ident,
                        start_ident=e.start_ident,
                        end_ident=e.end_ident,
                        label=e.label,
                        properties=e.properties.root.copy() if e.properties else {},
                        id=e.id,
                        start_id=e.start_id,
                        end_id=e.end_id,
                        start_label=start_label,
                        end_label=end_label
                    )
                )

        # 6. Edge updates (edges in both, but label, endpoints, or properties differ)
        for ident, e in b_edge_map.items():
            if ident in a_edge_map:
                a_e = a_edge_map[ident]

                # Compare labels and endpoints first
                edge_changed = (
                    e.label != a_e.label or
                    e.start_ident != a_e.start_ident or
                    e.end_ident != a_e.end_ident
                )

                # Compare properties by sorting keys and values into OrderedDicts
                def ordered(d):
                    if not isinstance(d, dict):
                        return d
                    return OrderedDict(sorted((k, ordered(v)) for k, v in d.items()))

                b_props = ordered(e.properties.root if e.properties else {})
                a_props = ordered(a_e.properties.root if a_e.properties else {})

                if not edge_changed:
                    # Only set edge_changed if properties differ
                    if b_props != a_props:
                        edge_changed = True

                if edge_changed:
                    if e.start_ident is None:
                        raise ValueError(f"Edge {e.ident} has no start_ident, cannot update.")
                    if e.end_ident is None:
                        raise ValueError(f"Edge {e.ident} has no end_ident, cannot update.")
                    # Look up start_label and end_label from vertices in graph_b
                    start_label = b_vertex_map[e.start_ident].label if e.start_ident in b_vertex_map else None
                    end_label = b_vertex_map[e.end_ident].label if e.end_ident in b_vertex_map else None
                    self.mutations.append(
                        AgMutation.update_edge(
                            ident=e.ident,
                            start_ident=e.start_ident,
                            end_ident=e.end_ident,
                            label=e.label,
                            properties=b_props.copy(),
                            id=e.id,
                            start_id=e.start_id,
                            end_id=e.end_id,
                            start_label=start_label,
                            end_label=end_label
                        )
                    )

    def to_cypher_statements(self) -> List[str]:
        """Convert all mutations to Cypher statements."""
        statements = []
        for mutation in self.mutations:
            if not isinstance(mutation, AgMutation):
                raise TypeError(f"Expected AgMutation, got {type(mutation).__name__}")
            statements.extend(mutation.to_statements())
        return statements
