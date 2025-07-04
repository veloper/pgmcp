from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import Field, field_validator, model_serializer, model_validator

from pgmcp.ag_entity import AgEntity


if TYPE_CHECKING:
    from pgmcp.ag_graph import AgGraph
    from pgmcp.ag_vertex import AgVertex
    from pgmcp.db import AgtypeRecord

class AgEdge(AgEntity):
    start_id: int | None = Field(default=None)
    end_id: int | None = Field(default=None)
    
    # ===================================================================
    # Model Validators
    # ===================================================================

    @model_validator(mode='after')
    def validate_start_end(self) -> Self:
        """Ensure exclusive validation for start_id and end_id -- both int, or both None."""

        
        # Attempt coercion
        if isinstance(self.start_id, str) and isinstance(self.end_id, str):
            self.start_id = int(self.start_id)
            self.end_id = int(self.end_id)
        
        # Both None?
        if self.start_id is None and self.end_id is None:
            return self
        
        # Both valid integers?
        if isinstance(self.start_id, int) and isinstance(self.end_id, int) and self.start_id >= 0 and self.end_id >= 0:
            return self
       
        raise ValueError(f"Invalid edge start_id ({self.start_id!r}) and end_id ({self.end_id!r}). Both must be integers >= 0 or both None.")

    # ===================================================================
    # Relationships
    # ===================================================================

    @property
    def start_vertex(self) -> AgVertex | None:
        """Get the start vertex of this edge."""
        return self.graph.vertices.get_by_ident(self.start_ident) if self.start_ident else None
    
    @property
    def end_vertex(self) -> AgVertex | None:
        """Get the end vertex of this edge."""
        return self.graph.vertices.get_by_ident(self.end_ident) if self.end_ident else None
    
    # ===================================================================
    # Model Serializer
    # ===================================================================
    @model_serializer
    def custom_serialize(self) -> dict:
        """Serialize to an _edge_ specific dict."""
        return {
            "id": self.id,
            "label": self.label,
            "properties": self.properties,
            "start_id": self.start_id,
            "end_id": self.end_id
        }
        
    
    # ===================================================================
    # Type Conversions: AgtypeRecord
    # ===================================================================

    @classmethod
    def from_agtype_record(cls, record: 'AgtypeRecord') -> Self:
        # Validate required fields for edge
        if not hasattr(record, 'label') or record.label is None:
            raise TypeError("AgEdge requires 'label' field in AgtypeRecord.")
        if not hasattr(record, 'properties') or not isinstance(record.properties, dict):
            raise TypeError("AgEdge requires 'properties' field as a dict in AgtypeRecord.")
        if not hasattr(record, 'start_id') or not hasattr(record, 'end_id'):
            raise TypeError("AgEdge requires 'start_id' and 'end_id' fields in AgtypeRecord.")
        return cls.model_validate({
            "id": record.id,
            "label": record.label,
            "properties": record.properties,
            "start_id": record.start_id,
            "end_id": record.end_id,
        })

    def to_agtype_record(self) -> 'AgtypeRecord':
        from pgmcp.db import AgtypeRecord  # Local import to break circular dependency
        return AgtypeRecord(
            label=self.label,
            id=self.id,
            properties=self.properties.root,
            start_id=self.start_id,
            end_id=self.end_id,
        )
