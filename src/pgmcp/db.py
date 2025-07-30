from __future__ import annotations

import json

from collections import UserList
from contextlib import AbstractAsyncContextManager, AsyncContextDecorator, AsyncExitStack
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Self, TypeVar

from sqlalchemy.engine import Row
from sqlalchemy.orm import declarative_base

from pgmcp.settings import get_settings


IDENT_PROPERTY = get_settings().age.ident_property

Base = declarative_base()

def decode_record(record: Row) -> dict:
    """
    Decode a single SQLAlchemy Row object containing AGE agtype strings
    into a dict.
    """
    result = {}
    for key, value in record.items():
        if isinstance(value, str) and '::' in value:
            # This is an agtype string, decode it
            value = decode_agtype_string(value)
        result[key] = value
    return result

def decode_agtype_string(agtype_string: str) -> Any:
    """
    Decode a single agtype string into a Python object.
    This function should be implemented to handle the specific
    agtype formats used in your database.
    """
    # Placeholder implementation - replace with actual decoding logic
    if agtype_string.startswith('{') and agtype_string.endswith('}'):
        # This looks like a JSON object
        return json.loads(agtype_string)
    elif agtype_string.startswith('[') and agtype_string.endswith(']'):
        # This looks like a JSON array
        return json.loads(agtype_string)
    else:
        # Fallback to returning the string itself
        return agtype_string

def decode_asyncio_agtype_recordset(records: list[Row]) -> list[dict]:
    """
    Efficiently decode a list of asyncpg.Record objects containing AGE agtype strings
    into a list of dicts, using a single json.loads call on a constructed JSON array.
    This version concatenates all agtype strings with commas, replaces '::vertex' and '::edge' with '',
    and wraps the result in brackets.
    """
    agtype_strings = [
        value for record in records
        for value in (record._mapping.values() if hasattr(record, '_mapping') else record.values())
        if isinstance(value, str) and '::' in value
    ]
    if not agtype_strings:
        return []

    # Concatenate all objects into one string, separated by commas
    concat = ','.join(agtype_strings)
    # Remove both ::vertex and ::edge suffixes from the string
    concat = concat.replace('::vertex', '')
    concat = concat.replace('::edge',   '')
    # Wrap in brackets to form a JSON array
    json_array = '[' + concat + ']'
    return json.loads(json_array)

@dataclass
class DbRecord:
    """A base class for database records with common functionality."""
    
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the record to a dictionary."""
        return asdict(self, dict_factory=dict)
    
    def to_json(self) -> str:
        """Convert the record to a JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_data: str) -> Self:
        """Convert a JSON string into a record."""
        data = json.loads(json_data)
        return cls.from_dict(data)

    
    



@dataclass
class AgtypeRecord(DbRecord):
    label      : str
    properties : Dict[str, Any] = field(default_factory=dict)
    id         : int | None = None
    start_id   : int | None = None
    end_id     : int | None = None


    _type       : Literal['vertex', 'edge'] | None = field(default=None, init=True, repr=False)

    def __post_init__(self):
        if self.label is None:
            raise TypeError("AgtypeRecord requires a 'label' field.")
        if self.properties is None:
            self.properties = {}

    @property
    def type(self) -> Literal['vertex', 'edge']:
        """Determine if this record is a vertex or an edge based on its properties."""
        if self._type is not None:
            return self._type # faster if set.
        return 'edge' if self.start_id is not None and self.end_id is not None else 'vertex'
    
    @property
    def is_vertex(self) -> bool: return self.type == 'vertex'
    
    @property
    def is_edge(self) -> bool: return self.type == 'edge'

    @classmethod
    def from_raw_records(cls, records: List[Row]) -> List[Self]:
        """Convert a list of asyncpg.Record to a list of DbRecord."""
        dicts : List[Dict] = decode_asyncio_agtype_recordset(records)
        return [cls.from_dict(record) for record in dicts]
