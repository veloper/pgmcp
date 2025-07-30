from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from pydantic import field_validator

from pgmcp.ag_entity import AgEntity
from pgmcp.ag_properties import AgProperties
from pgmcp.settings import get_settings
from pgmcp.utils import deep_merge


IDENT_PROPERTY: str = get_settings().age.ident_property

if TYPE_CHECKING:
    from pgmcp.ag_graph import AgGraph
    from pgmcp.db import AgtypeRecord


class AgVertex(AgEntity):
    
    # ===================================================================
    # Field Validators
    # ===================================================================
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, val: Any) -> int | None:
        """Ensure id is an integer or None."""
        value : int | None = val
        
        # Coerce string to int or None
        if isinstance(value, str): 
            value = int(value) if value.isdigit() else None
        
        # Validate type
        if value is not None and not (isinstance(value, int) and value > 0):
            raise ValueError("ID must be either an integer > 0 or None.")

        return value
    
    @field_validator('label', mode='before')
    @classmethod
    def validate_label(cls, value: str) -> str:
        """Ensure label is a non-empty string."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Label must be a non-empty string.")
        return value.strip()

    

    def to_agtype_record(self) -> 'AgtypeRecord':
        from pgmcp.db import AgtypeRecord  # Local import to break circular dependency
        properties = dict(self.properties)
        properties.update({
            "ident": self.ident if self.has_ident else None,
        })
        
        return AgtypeRecord(
            label=self.label,
            id=self.id,
            properties=properties
        )

    # ===================================================================
    # Helpers
    # ===================================================================
    
    
    def upsert(self, *, label: str | None = None, properties: dict | None = None) -> Self:
        """Upsert this edge using a non-destructive deep-merge.
        
        - Protects critical properties like ident, start_ident, and end_ident.
        - Merges in the most non-destructive way possible.
        - If label is provided, it will update the edge's label.
        """
        if label and label != self.label:
            self.label = label
            
        if properties:
            original_properties = self.properties.model_dump()
            incoming_properties = properties
            merged_properties = deep_merge(original_properties, incoming_properties)
            
            # Ensure critical information is not lost
            merged_properties[IDENT_PROPERTY] = self.ident if self.has_ident else None
            
            self.properties = AgProperties.model_validate(merged_properties)
            
        return self
