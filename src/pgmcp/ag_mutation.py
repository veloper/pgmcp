from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Dict, List, Literal

from pgmcp.settings import get_settings


settings = get_settings()

"""
REQUIRED_PROPERTY_KEYS 
These are the property keys that uniquely identify vertices and edges in both AGE and Ag* class systems.

- These keys are essential for mapping between the AGE graph's strict integer-based identifiers and the Ag* classes' string-based identifiers.
- They are used to ensure that mutations can be applied correctly, especially when converting between different graph representations."""

REQUIRED_PROPERTY_KEYS = [
    settings.age.ident_property,
    settings.age.start_ident_property,
    settings.age.end_ident_property
]
REQUIRED_VERTEX_PROPERTY_KEYS = [ settings.age.ident_property ]
REQUIRED_EDGE_PROPERTY_KEYS = REQUIRED_PROPERTY_KEYS

@dataclass
class AgMutation:
    """A simple data class to represent an atomic mutation operation"""
    operation   : Literal['add', 'remove', 'update']         = field()
    entity      : Literal['vertex', 'edge']                  = field()
    ident       : str                                        = field()
    label       : str                                        = field()
    start_ident : str | None                                 = field(default=None)
    end_ident   : str | None                                 = field(default=None)
    properties  : Dict[str, Any]                             = field(default_factory=dict)  

    # Optional Fields
    id          : int | None                                 = field(default=None)  # agtype.id, if available
    start_id    : int | None                                 = field(default=None)  # agtype.start_id,
    end_id      : int | None                                 = field(default=None)  # agtype.end_id, if available
    # New fields for endpoint labels
    start_label : str | None                                 = field(default=None)
    end_label   : str | None                                 = field(default=None)


    def __post_init__(self):
        self.ensure_properties_have_required_keys_and_values()

    def ensure_properties_have_required_keys_and_values(self) -> None:
        """Ensure that the properties dictionary contains the required keys and values."""
        props = dict(self.properties) if self.properties is not None else {}
        # 1. Set all required keys to None if missing
        if self.is_vertex:
            for key in REQUIRED_VERTEX_PROPERTY_KEYS:
                if key not in props:
                    props[key] = None
        elif self.is_edge:
            for key in REQUIRED_EDGE_PROPERTY_KEYS:
                if key not in props:
                    props[key] = None
        # 2. Set all required keys to the correct value from the instance
        if self.is_vertex:
            for key in REQUIRED_VERTEX_PROPERTY_KEYS:
                props[key] = getattr(self, key)
        elif self.is_edge:
            for key in REQUIRED_EDGE_PROPERTY_KEYS:
                props[key] = getattr(self, key)
        self.properties = props



    @cached_property
    def is_vertex(self) -> bool: return self.entity == 'vertex'
    
    @cached_property
    def is_edge(self) -> bool: return self.entity == 'edge'
    
    @cached_property
    def is_addition(self) -> bool: return self.operation == 'add'

    @cached_property
    def is_removal(self) -> bool: return self.operation == 'remove'

    @cached_property
    def is_update(self) -> bool: return self.operation == 'update'
    
    @classmethod
    def add_edge( 
        cls, ident: str, start_ident: str, end_ident: str, label: str, properties: Dict[str, Any], *,
        id: int | None = None, start_id: int | None = None, end_id: int | None = None, start_label: str | None = None, end_label: str | None = None, **kwargs
    ) -> AgMutation:
        return cls(operation='add', entity='edge', ident=ident, label=label,
                   start_ident=start_ident, end_ident=end_ident, properties=properties,
                   id=id, start_id=start_id, end_id=end_id, start_label=start_label, end_label=end_label, **kwargs)

    @classmethod
    def remove_edge(
        cls, ident: str, label: str, *,
        id: int | None = None, start_id: int | None = None, end_id: int | None = None, start_ident: str | None = None, end_ident: str | None = None, **kwargs
    ) -> AgMutation:
        return cls(operation='remove', entity='edge', ident=ident, label=label,
                   id=id, start_id=start_id, end_id=end_id, start_ident=start_ident, end_ident=end_ident, **kwargs)

    @classmethod
    def update_edge(
        cls, ident: str, start_ident: str, end_ident: str, label: str, properties: Dict[str, Any], *,
        id: int | None = None, start_id: int | None = None, end_id: int | None = None, start_label: str | None = None, end_label: str | None = None, **kwargs
    ) -> AgMutation:
        return cls(operation='update', entity='edge', ident=ident, label=label,
                   start_ident=start_ident, end_ident=end_ident, properties=properties,
                   id=id, start_id=start_id, end_id=end_id, start_label=start_label, end_label=end_label, **kwargs)

    @classmethod
    def add_vertex(
        cls, ident: str, label: str, properties: Dict[str, Any], *,
        id: int | None = None, **kwargs
    ) -> AgMutation:
        return cls(operation='add', entity='vertex', ident=ident, label=label, properties=properties, id=id, **kwargs)
    
    @classmethod
    def remove_vertex(
        cls, ident: str, label: str, *,
        id: int | None = None, **kwargs
    ) -> AgMutation:
        return cls(operation='remove', entity='vertex', ident=ident, label=label, id=id, **kwargs)

    @classmethod
    def update_vertex(
        cls, ident: str, label: str, properties: Dict[str, Any], *,
        id: int | None = None, **kwargs
    ) -> AgMutation:
        return cls(operation='update', entity='vertex', ident=ident, label=label, properties=properties, id=id, **kwargs)
            
    def to_statements(self) -> list[BaseCypherStatement]:
        """Return a list of Cypher statements for this mutation (plural form)."""
        if self.is_edge and (self.is_addition or self.is_update):
            if not self.start_ident or not self.end_ident:
                raise ValueError("Edge mutations require both start_ident and end_ident to be set.")
            return [
                UpsertEdgeCypherStatement(
                    is_update=self.is_update,
                    is_addition=self.is_addition,
                    ident=self.ident,
                    label=self.label,
                    start_ident=self.start_ident,
                    end_ident=self.end_ident,
                    properties=self.properties,
                    id=self.id,
                    start_id=self.start_id,
                    end_id=self.end_id,
                    start_label=self.start_label,
                    end_label=self.end_label,
                ),
            ]
        elif self.is_edge and self.is_removal:
            if not self.start_ident or not self.end_ident:
                raise ValueError("Edge mutations require both start_ident and end_ident to be set.")
            return [DeleteEdgeCypherStatement(
                ident=self.ident,
                label=self.label,
                start_ident=self.start_ident,
                end_ident=self.end_ident,
                id=self.id,
            )]
        elif self.is_vertex and (self.is_addition or self.is_update):
            return [UpsertVertexCypherStatement(
                is_update=self.is_update,
                is_addition=self.is_addition,
                ident=self.ident,
                label=self.label,
                properties=self.properties or {},
                id=self.id,
            )]
        elif self.is_vertex and self.is_removal:
            return [DeleteVertexCypherStatement(
                ident=self.ident,
                label=self.label,
                id=self.id,
            )]
        else:
            raise ValueError(f"Unsupported mutation type: {self.operation} for {self.entity}")
        


@dataclass
class BaseCypherStatement:
    """Base class for Cypher queries, providing a common interface."""
    ident : str = field(metadata={"description": "agtype.properties.ident"}, init=True)
    label : str = field(metadata={"description": "agtype.label"}, init=True)
    
    
    @abstractmethod
    def clauses(self) -> list[str]:
        """Generates all of the Cypher clauses for this mutation to effectuate the change."""
        raise NotImplementedError("Subclasses must implement this method.")
        
    @abstractmethod
    def validate(self) -> None:
        """Validate the Cypher statement. This method should be overridden by subclasses to implement specific validation logic."""
        raise NotImplementedError("Subclasses must implement this method.")
    
        
    def __post_init__(self):
        # No property injection here; all handled in classmethods
        pass
    
    # ===============================================================
    # Validation Methods
    # ===============================================================

    def validate_all_required_properties_present(self, properties: Dict[str, Any]):
        """Check if, for this instance, given a dict of properties, do those properties contain all required keys with present values."""
        
        # All must exist
        values = [properties.get(key) for key in (REQUIRED_VERTEX_PROPERTY_KEYS if self.is_vertex else REQUIRED_EDGE_PROPERTY_KEYS)]
        
        if len(values) != len(REQUIRED_VERTEX_PROPERTY_KEYS):
            raise ValueError(f"{self.__class__.__name__} requires properties to contain all required keys: {REQUIRED_VERTEX_PROPERTY_KEYS}")
        
        if any(value for value in values if value is None or value.strip() == ""):
            raise ValueError(f"{self.__class__.__name__} requires properties to contain all required keys with non-empty values: {REQUIRED_VERTEX_PROPERTY_KEYS}")
    
    @property
    def is_vertex(self) -> bool: return "Vertex" in self.__class__.__name__

    @property
    def is_edge(self) -> bool: return "Edge" in self.__class__.__name__

    def quote_string(self, value: str) -> str:
        """Quote a python string for use directly in a Cypher query. (auto escapes the input string)"""
        return f"'{self.escape_string(value)}'"

    def escape_string(self, value: str) -> str:
        """Escape a python string for use in a Cypher query, this is not a security measure, but a syntax measure."""
        # Escape backslash first, then single and double quotes
        value = value.replace("\\", "\\\\")
        value = value.replace("'", "\\'")
        value = value.replace('"', '\\"')
        return value

    def encode_keyword(self, keyword: str) -> str:
        """Encode a Cypher keyword to a double-quoted string if it contains spaces, punctuation, or is a reserved word."""
        # Cypher keywords with spaces, punctuation, or reserved words must be double-quoted
        # if not keyword.isidentifier():
        #     safe_keyword = keyword.replace('"', '\\"')
        #     return f'"{safe_keyword}"'
        return keyword
    
    def encode_dict_for_set(self, alias: str, data: Dict[str, Any]) -> str:
        """It's a well known issue with property propagation on edge assignment that the map approach does not work, thus
        we must use an assignment approach for the properties, which is a Cypher-specific syntax.
        """
        assignments = []
        for k, v in data.items():
            encoded_key = self.encode_keyword(str(k))
            if isinstance(v, str):
                encoded_value = self.quote_string(v)
            elif isinstance(v, bool):
                encoded_value = "true" if v else "false"
            elif v is None:
                encoded_value = "null"
            elif isinstance(v, (int, float)):
                encoded_value = str(v)
            elif isinstance(v, dict):
                encoded_value = self.encode_dict_for_set(alias, v)
            elif isinstance(v, list):
                encoded_value = "[" + ", ".join(self.quote_string(str(item)) for item in v) + "]"
            else:
                raise TypeError(f"Unsupported value type for Cypher encoding: {type(v)}")
            
            assignments.append(f"{alias}.{encoded_key} = {encoded_value}")
        return ", ".join(assignments)
        
        
    
    def encode_dict(self, data: Dict[str, Any]) -> str:
        """Encode a python dictionary to a Cypher-compatible string for its {key: value} properties syntax."""
        def encode_value(val):
            if isinstance(val, str):
                return self.quote_string(val)
            elif isinstance(val, bool):
                return "true" if val else "false"
            elif val is None:
                return "null"
            elif isinstance(val, (int, float)):
                return str(val)
            elif isinstance(val, dict):
                return self.encode_dict(val)
            elif isinstance(val, list):
                return "[" + ", ".join(encode_value(v) for v in val) + "]"
            else:
                raise TypeError(f"Unsupported value type for Cypher encoding: {type(val)}")
    
        
        items = []
        for k, v in data.items():
            items.append(f"{self.encode_keyword(str(k))}: {encode_value(v)}")
            
        return "{" + ", ".join(items) + "}"
        

    def __str__(self) -> str:
        """Attempts to generate a Cypher query string for this mutation."""
        return " ".join(self.clauses())

    def to_str(self) -> str:
        """Attempts to generate a Cypher query string for this mutation."""
        return str(self)

@dataclass
class UpsertVertexCypherStatement(BaseCypherStatement):
    """A stand alone class taking in the required fields to properly construct a Cypher query for an upsert operation."""

    is_update   : bool          = field(default=False, init=True)  # Whether this is an update operation
    is_addition : bool          = field(default=True, init=True)   # Whether this
    properties : Dict[str, Any] = field(default_factory=dict, init=True)
    id         : int | None     = field(default=None, init=True)  # agtype.id, if available
    
    def validate(self) -> None:
        """Validate the fields of this upsert operation."""
        if not self.label or not self.label.strip():
            raise ValueError("UpsertVertexCypherStatement requires a non-empty label.")
        self.validate_all_required_properties_present(self.properties)

    def clauses(self) -> List[str]:
        """Generates the **Cypher** clauses that fulfill this mutation."""

        clauses = []
        label = self.encode_keyword(self.label)
        keyword = self.encode_keyword("id" if self.id else "ident")
        identifier = int(self.id) if self.id else self.quote_string(str(self.ident))
        properties = self.encode_dict(self.properties)

        if "ident" not in self.properties or not self.properties["ident"]:
            raise ValueError("UpsertVertexCypherStatement requires 'ident' in properties to be set.")

        if self.is_addition:
            clauses.append("CREATE (n:%s %s)" % (label, properties))
        else:
            # Use MATCH for updates to existing vertices
            clauses.append("MATCH (n:%s {%s: %s})" % (label, keyword, identifier))
            clauses.append("SET n += %s" % self.encode_dict_for_set("n", self.properties))

        return clauses


@dataclass
class DeleteVertexCypherStatement(BaseCypherStatement):
    
    id : int | None = field(default=None, init=True)  # agtype.id, if available
    
    def validate(self):
        pass
    
    def clauses(self): 
        """Generates the **Cypher** clauses that fulfill this mutation."""
        
        clauses = []
        
        # 1. MATCH (Vertex to Delete)
        label = self.encode_keyword(self.label)
        keyword = self.encode_keyword("id" if self.id else "ident")
        identifier = int(self.id) if self.id else self.quote_string(str(self.ident))
        clauses.append("MATCH (n:%s {%s: %s})" % (label, keyword, identifier)) 
        
        # 2. DETACH DELETE (Delete Vertex)
        clauses.append("DETACH DELETE n")
        
        return clauses

@dataclass
class UpsertEdgeCypherStatement(BaseCypherStatement):
    """Upserts the edge properties only, assuming the edge record already exists."""

    is_update   : bool          = field(default=False, init=True)  # Whether this is an update operation
    is_addition : bool          = field(default=True, init=True)   # Whether this is an addition operation
    properties  : Dict[str, Any] = field(default_factory=dict, init=True)  # agtype.properties
    id          : int | None     = field(default=None, init=True)  # agtype.id, if available
    start_id    : int | None    = field(default=None, init=True)  # agtype.start_id, if available
    end_id      : int | None    = field(default=None, init=True)  # agtype.end_id, if available
    start_ident : str | None    = field(default=None, init=True)  # agtype.start_ident, if available
    end_ident   : str | None    = field(default=None, init=True)  # agtype.end_ident, if available
    start_label : str | None    = field(default=None, init=True)  # Optionally allow explicit labels
    end_label   : str | None    = field(default=None, init=True)  # Optionally allow explicit labels
    
    
    def validate(self):
        if not self.start_label or not self.start_label.strip():
            raise ValueError("UpsertEdgeCypherStatement requires a non-empty start_label.")
        if not self.end_label or not self.end_label.strip():
            raise ValueError("UpsertEdgeCypherStatement requires a non-empty end_label.")
        self.validate_all_required_properties_present(self.properties)
    
    def clauses(self) -> List[str]:
        """Generates the **Cypher** clauses that fulfill this mutation."""
        
        clauses = []
        start_label = self.encode_keyword(self.start_label) if self.start_label else ""
        start_keyword = self.encode_keyword(settings.age.ident_property)

        end_label = self.encode_keyword(self.end_label) if self.end_label else ""
        end_keyword = self.encode_keyword(settings.age.ident_property)
        
        start_ident = self.quote_string(str(self.start_ident))
        end_ident = self.quote_string(str(self.end_ident))
        
        edge_label = self.encode_keyword(self.label)
        edge_properties = self.encode_dict(self.properties)

        clauses.append("MATCH (a:%s {%s: %s})" % (start_label, start_keyword, start_ident))
        clauses.append("MATCH (b:%s {%s: %s})" % (end_label, end_keyword, end_ident))
        clauses.append("MERGE (a)-[e:%s %s]->(b)" % (edge_label, edge_properties))
        
        return clauses

@dataclass
class DeleteEdgeCypherStatement(BaseCypherStatement):
    
    start_ident : str           = field(metadata={"description": "agtype.start_ident"}, init=True)
    end_ident   : str           = field(metadata={"description": "agtype.end_ident"}, init=True)
    id          : int | None    = field(default=None, init=True)  # agtype.id, if available
    start       : int | None    = field(default=None, init=True)  # agtype.start_id, if available
    end         : int | None    = field(default=None, init=True)  # agtype.end_id, if available

    def validate(self):
        pass
    
    def clauses(self) -> List[str]:
        """Generates the **Cypher** clauses that fulfill this mutation."""
        
        clauses = []

        label = self.encode_keyword(self.label)
        start_keyword = self.encode_keyword("start_id" if self.start else settings.age.start_ident_property)
        end_keyword = self.encode_keyword("end_id" if self.end else settings.age.end_ident_property)
        start_value = int(self.start) if self.start else self.quote_string(str(self.start_ident))
        end_value = int(self.end) if self.end else self.quote_string(str(self.end_ident))

        # 1. MATCH (Edge to Delete)
        # Use 'e' as the idiomatic alias for edges
        clauses.append(
            "MATCH ()-[e:%s {%s: %s, %s: %s}]->()" % (
                label,
                start_keyword, start_value,
                end_keyword, end_value
            )
        )
        
        # 2. DELETE (Edge)
        clauses.append("DELETE e")
        
        return clauses

