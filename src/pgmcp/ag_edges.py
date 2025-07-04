from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict

from pgmcp.ag_edge import AgEdge
from pgmcp.ag_query_builder import AgQueryBuilderEdge
from pgmcp.list_root_model import ListRootModel


class AgEdges(ListRootModel[AgEdge]):
    """A list of edges with optimizations for fast access, common tasks, and serialization."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    
    # =========================================================
    # Query Builder Methods
    # ---------------------------------------------------------
    # A bit of a loop around, but it allows a much nicer
    # "api-feel" of: `graph.edges.label("RELATIONSHIP").all()`
    # =========================================================

    def query(self)                          -> AgQueryBuilderEdge:
        if graph := self.graph:
            return AgQueryBuilderEdge.from_ag_graph(graph) 
        raise ValueError(
            "The 'graph' property is not set on this AgVertices instance. "
            "This usually means you're trying to access query methods before the model is fully initialized, "
            "such as within a Pydantic validator. "
            "Ensure the model is fully constructed before calling query methods. "
            "If you have a direct reference to the graph, use AgQueryBuilderEdge.from_ag_graph(graph) instead."
        )
        
    def filter(self, **kwargs)               -> AgQueryBuilderEdge: return self.query().filter(**kwargs)
    def ident(self, ident: str)              -> AgQueryBuilderEdge: return self.query().ident(ident)
    def start_ident(self, start_ident: str)  -> AgQueryBuilderEdge: return self.query().start_ident(start_ident)
    def end_ident(self, end_ident: str)      -> AgQueryBuilderEdge: return self.query().end_ident(end_ident)
    def label(self, label: str)              -> AgQueryBuilderEdge: return self.query().label(label)
    def prop(self, key: str, value: Any)     -> AgQueryBuilderEdge: return self.query().prop(key, value)
    def props(self, **kwargs: Any)           -> AgQueryBuilderEdge: return self.query().props(**kwargs)

    def get_by_ident(self, ident: str) -> AgEdge | None:
        return self.query().ident(ident).first()
