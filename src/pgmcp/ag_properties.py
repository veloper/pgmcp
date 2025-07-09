from __future__ import annotations

from typing import Any, ClassVar, Dict

from pydantic import ConfigDict, Field, RootModel, model_serializer

from pgmcp.royal_description import RoyalDescription
from pgmcp.settings import get_settings


settings = get_settings()
IDENT_PROPERTY      : str = settings.age.ident_property
START_IDENT_PROPERTY: str = settings.age.start_ident_property
END_IDENT_PROPERTY  : str = settings.age.end_ident_property

def generate_ident() -> str:
    """Generate a new identifier."""
    return RoyalDescription.generate(3, delimiter='_')  # Use '_' to prevent issues with stemming, n-gramming, etc.

class AgProperties(RootModel[dict[str, Any]]):
    


    """An (Observable)dict to hold properties for vertices and edges."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    root: dict[str, Any] = Field(default_factory=dict)

    # ===================================================================
    # Model Serializers
    # ===================================================================
    
    @model_serializer
    def custom_serialize(self) -> dict:
        """Serialize to a dict, excluding unserializable/circular refs like 'graph'."""
        result : Dict[str, Any] = {}
        for key, value in self.root.items():
            # Exclude known non-serializable/circular keys
            if key == 'graph':
                continue
            # Optionally, skip any value that is not a primitive or dict/list
            if hasattr(value, '__dict__') or hasattr(value, '__class__') and not isinstance(value, (str, int, float, bool, dict, list, type(None))):
                continue
            result[key] = value
        return result
    
    # ===================================================================
    # Properties
    # ===================================================================
        
    @property
    def ident(self) -> str: return self.root[IDENT_PROPERTY]

    @ident.setter
    def ident(self, value: str | None) -> None: self.root[IDENT_PROPERTY] = value

    @property
    def has_ident(self) -> bool: return IDENT_PROPERTY in self.root and self.root[IDENT_PROPERTY] is not None

    @property
    def start_ident(self) -> str | None: return self.root.get(START_IDENT_PROPERTY, None)

    @start_ident.setter
    def start_ident(self, value: str | None) -> None: self.root[START_IDENT_PROPERTY] = value
    
    @property
    def has_start_ident(self) -> bool: return START_IDENT_PROPERTY in self.root and self.root[START_IDENT_PROPERTY] is not None

    @property
    def end_ident(self) -> str | None: return self.root.get(END_IDENT_PROPERTY, None)

    @end_ident.setter
    def end_ident(self, value: str | None) -> None: self.root[END_IDENT_PROPERTY] = value

    @property
    def has_end_ident(self) -> bool: return END_IDENT_PROPERTY in self.root and self.root[END_IDENT_PROPERTY] is not None
    
    # ===================================================================
    # Mapping Methods
    # ===================================================================

    def get(self, key: str, default: Any = None) -> Any: return self.root.get(key, default)
    def __getitem__(self, key: str) -> Any: return self.root[key]
    def __setitem__(self, key: str, value: Any) -> None:
        if key == 'graph':
            # Never allow 'graph' to be set as a property
            return
        self.root[key] = value

    def __delitem__(self, key: str) -> None: del self.root[key]
    def __contains__(self, key: str) -> bool: return key in self.root
    def __iter__(self): return iter(self.root)
    def __len__(self) -> int: return len(self.root)
    def __repr__(self) -> str: return f"{self.__class__.__name__}({repr(self.root)})"
    def __str__(self) -> str: return str(self.root)
    def __eq__(self, other) -> bool:
        if isinstance(other, AgProperties): return self.root == other.root
        if isinstance(other, dict): return dict(self.root) == other
        return False
    def __ne__(self, other) -> bool: return not self.__eq__(other)
    def __bool__(self) -> bool: return bool(self.root)
    def __copy__(self): return self.__class__(root=self.root.copy())
    def __deepcopy__(self, memo):
        import copy; return self.__class__(root=copy.deepcopy(self.root, memo))
    def copy(self): return self.__class__(root=self.root.copy())
    def clear(self) -> None: self.root.clear()
    def keys(self): return self.root.keys()
    def values(self): return self.root.values()
    def items(self): return self.root.items()
    def pop(self, key: str, default: Any = None) -> Any: return self.root.pop(key, default)
    def popitem(self): return self.root.popitem()
    def setdefault(self, key: str, default: Any = None) -> Any: return self.root.setdefault(key, default)
    def update(self, *args, **kwargs) -> None:
        # Remove 'graph' if present in any update
        d = dict(*args, **kwargs)
        d.pop('graph', None)
        self.root.update(d)
