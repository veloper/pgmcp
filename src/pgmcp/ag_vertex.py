from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from pydantic import field_validator

from pgmcp.ag_entity import AgEntity


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

    # ===================================================================
    # Type Conversion
    # ===================================================================
    
    @classmethod
    def from_agtype_record(cls, record: 'AgtypeRecord') -> Self:
        # Validate required fields for vertex
        if not hasattr(record, 'properties') or not isinstance(record.properties, dict):
            raise TypeError("AgVertex requires 'properties' field as a dict in AgtypeRecord.")
        return cls.model_validate({
            "id": record.id,
            "label": record.label,
            "properties": record.properties,
        })

    def to_agtype_record(self) -> 'AgtypeRecord':
        from pgmcp.db import AgtypeRecord  # Local import to break circular dependency
        return AgtypeRecord(
            label=self.label,
            id=self.id,
            properties=self.properties.root
        )
