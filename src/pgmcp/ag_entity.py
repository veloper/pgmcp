from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from pgmcp.ag_properties import AgProperties


if TYPE_CHECKING:
    from pgmcp.ag_edge import AgEdge
    from pgmcp.ag_graph import AgGraph
    from pgmcp.ag_vertex import AgVertex
    from pgmcp.db import AgtypeRecord

class AgEntity(BaseModel):
    """A base model for Apache AGE agtype, which can be a vertex or an edge."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    label: str
    id: int | None = None
    properties: AgProperties = Field(default_factory=AgProperties)

    # ===================================================================
    # Private Attributes
    # ===================================================================

    _graph: AgGraph | None = PrivateAttr(default=None)
        
    # ===================================================================
    # Model Validator to Modify the incoming model_validate(DICT) so 
    # that we can redirect top level `ident`, `start_ident`, and `end_ident`
    # into properties.
    # ===================================================================
    @model_validator(mode="before")
    @classmethod
    def _redirect_properties(cls, values: dict) -> dict:
        """
        Redirects top-level `ident`, `start_ident`, and `end_ident` into the properties field.
        This allows us to keep these fields as first-class citizens in the graph.
        """
        if not isinstance(values, dict): return values
        props = values.get("properties", {})

        if "ident" in values:
            props["ident"] = values.pop("ident")

        if "start_ident" in values:
            props["start_ident"] = values.pop("start_ident")

        if "end_ident" in values:
            props["end_ident"] = values.pop("end_ident")

        values["properties"] = props
        return values

    # ===================================================================
    # Properties
    # - these are first class citizens in the graph, but exist in the
    #   properties as their own dedicated fields
    # ===================================================================

    @property
    def graph(self) -> AgGraph:
        if self._graph is None:
            raise ValueError("Graph is not set for this entity.")
        return self._graph

    @graph.setter
    def graph(self, value: AgGraph | None) -> None: self._graph = value

    @property
    def ident(self) -> str: return self.properties.ident

    @ident.setter
    def ident(self, value: str) -> None: self.properties.ident = value

    @property
    def has_ident(self) -> bool: return self.properties.has_ident

    @property
    def start_ident(self) -> str | None: return self.properties.start_ident

    @start_ident.setter
    def start_ident(self, value: str | None) -> None: self.properties.start_ident = value

    @property
    def has_start_ident(self) -> bool: return self.properties.has_start_ident

    @property
    def end_ident(self) -> str | None: return self.properties.end_ident

    @end_ident.setter
    def end_ident(self, value: str | None) -> None: self.properties.end_ident = value
    
    @property
    def has_end_ident(self) -> bool: return self.properties.has_end_ident

    # ===================================================================
    # Helpers
    # ===================================================================

    @property
    def is_vertex(self) -> bool:
        from pgmcp.ag_vertex import AgVertex
        return isinstance(self, AgVertex)

    @property
    def is_edge(self) -> bool:
        from pgmcp.ag_edge import AgEdge
        return isinstance(self, AgEdge)


    # ===================================================================
    # Type Conversion: Agtype Record
    # ===================================================================

    @classmethod
    def from_agtype_record(cls, record: AgtypeRecord) -> Union[AgVertex, AgEdge]:
        # Circular import workaround
        from pgmcp.ag_edge import AgEdge
        from pgmcp.ag_vertex import AgVertex
        if record.is_vertex:
            return AgVertex.from_agtype_record(record)
        return AgEdge.from_agtype_record(record)

    @abstractmethod
    def to_agtype_record(self) -> AgtypeRecord:
        raise NotImplementedError("Subclasses must implement to_agtype_record method.")

