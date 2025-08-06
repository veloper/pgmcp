"""Metadata for a chunk, using RootModel to ensure dict-like behavior."""

from typing import Any, Dict

from pydantic import Field, RootModel, model_serializer


class ChunkMeta(RootModel[Dict[str, Any]]):
    """Metadata for a chunk, using RootModel to ensure dict-like behavior."""
    
    root: Dict[str, Any] = Field(default_factory=dict)
    
    @model_serializer
    def serialize(self) -> Dict[str, Any]:
        return self.root
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def __getitem__(self, key: str) -> Any:
        return self.root[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        self.root[key] = value
    
    def __delitem__(self, key: str) -> None:
        del self.root[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self.root
    
    def __len__(self) -> int:
        return len(self.root)
    
    def items(self):
        return self.root.items()
