from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import Field, field_validator, model_serializer, model_validator

from pgmcp.ag_entity import AgEntity, AgProperties
from pgmcp.settings import get_settings
from pgmcp.utils import deep_merge


IDENT_PROPERTY: str = get_settings().age.ident_property
START_IDENT_PROPERTY: str = get_settings().age.start_ident_property
END_IDENT_PROPERTY: str = get_settings().age.end_ident_property

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
    def validate_start_id_and_end_id(self) -> Self:
        """Ensure exclusive validation for start_id and end_id -- both int XOR both None."""
        
        # Attempt coercion
        if isinstance(self.start_id, str) and isinstance(self.end_id, str):
            self.start_id = int(self.start_id)
            self.end_id = int(self.end_id)
        
        # Check types
        start_type = type(self.start_id)
        end_type = type(self.end_id)
        valid_types = (int, type(None))
        
        # Type Mismatch?
        if start_type != end_type:
            raise ValueError(f"start_id ({self.start_id!r}) and end_id ({self.end_id!r}) must be of the same type (both int or both None).")
        
        # Invalid Types?
        if start_type not in valid_types or end_type not in valid_types:
            if start_type not in valid_types:
                raise ValueError(f"start_id ({self.start_id!r}) must be an int or None.")
            if end_type not in valid_types:
                raise ValueError(f"end_id ({self.end_id!r}) must be an int or None.")
        
        return self


    @model_validator(mode='after')
    def validate_start_ident_and_end_ident(self) -> Self:
        """These my not be none ever. This model is invalid is these are not found in edge properties."""
        if not self.has_start_ident:
            raise ValueError("start_ident must be set for AgEdge.")
        
        if not self.has_end_ident:
            raise ValueError("end_ident must be set for AgEdge.")
        
        return self
    
    
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
        
    
    # 
    def to_agtype_record(self) -> 'AgtypeRecord':
        from pgmcp.db import AgtypeRecord  # Local import to break circular dependency
        properties = dict(self.properties)
        properties.update({
            "ident": self.ident if self.has_ident else None,
            "start_ident": self.start_ident if self.has_start_ident else None,
            "end_ident": self.end_ident if self.has_end_ident else None,
        })
        return AgtypeRecord(
            label=self.label,
            id=self.id,
            properties=properties,
            start_id=self.start_id,
            end_id=self.end_id,
        )

    # ===================================================================
    # Helpers
    # ===================================================================
    
    def upsert(self, *, label: str | None = None, properties: dict | None = None) -> Self:
        """Upsert this edge using a non-destructive deep-merge.
        
        - Protects critical properties like ident, start_ident, and endIdent.
        - Merges in the most non-destructive way possible.
        - If label is provided, it will update the edge's label.
        """
        if label and label != self.label:
            self.label = label
            
        if properties:
            original_properties = self.properties.model_dump()
            incoming_properties = properties
            merged_properties = deep_merge(original_properties, incoming_properties)
            
            ident = merged_properties.get(IDENT_PROPERTY, self.ident)
            start_ident = merged_properties.get(START_IDENT_PROPERTY, self.start_ident)
            end_ident = merged_properties.get(END_IDENT_PROPERTY, self.end_ident)

            # Ensure critical information is not lost
            merged_properties[IDENT_PROPERTY] = ident
            merged_properties[START_IDENT_PROPERTY] = start_ident
            merged_properties[END_IDENT_PROPERTY] = end_ident

            self.properties = AgProperties.model_validate(merged_properties)
            
        return self
