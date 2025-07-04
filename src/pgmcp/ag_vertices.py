from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator

from pydantic import ConfigDict

from pgmcp.ag_query_builder import AgQueryBuilderVertex
from pgmcp.ag_vertex import AgVertex
from pgmcp.list_root_model import ListRootModel


class AgVertices(ListRootModel[AgVertex]):
    """A list of vertices with optimizations for fast access, common tasks, and serialization."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    
    # =========================================================
    # Query Builder Methods
    # ---------------------------------------------------------
    # A bit of a loop around, but it allows a much nicer
    # "api-feel" of: `graph.vertices.label("RELATIONSHIP").all()`
    # =========================================================

    def query(self)                          -> AgQueryBuilderVertex: 
        if graph := self.graph:
            return AgQueryBuilderVertex.from_ag_graph(graph) 
        raise ValueError(
            "The 'graph' property is not set on this AgVertices instance. "
            "This usually means you're trying to access query methods before the model is fully initialized, "
            "such as within a Pydantic validator. "
            "Ensure the model is fully constructed before calling query methods. "
            "If you have a direct reference to the graph, use AgQueryBuilderVertex.from_ag_graph(graph) instead."
        )
    
    def filter(self, **kwargs)               -> AgQueryBuilderVertex: return self.query().filter(**kwargs)
    def ident(self, ident: str)              -> AgQueryBuilderVertex: return self.query().ident(ident)
    def label(self, label: str)              -> AgQueryBuilderVertex: return self.query().label(label)
    def prop(self, key: str, value: Any)     -> AgQueryBuilderVertex: return self.query().prop(key, value)
    def props(self, **kwargs: Any)           -> AgQueryBuilderVertex: return self.query().props(**kwargs)

    def get_by_ident(self, ident: str) -> AgVertex | None:
        return self.query().ident(ident).first()
