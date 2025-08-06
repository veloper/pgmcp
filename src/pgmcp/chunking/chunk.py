from __future__ import annotations

import json

from typing import TYPE_CHECKING, Any, Dict

from pydantic import BaseModel, Field, model_serializer

from pgmcp.chunking.chunk_meta import ChunkMeta


if TYPE_CHECKING:
    from pgmcp.chunking.encodable_chunk import EncodableChunk

class Chunk(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    meta: ChunkMeta = Field(default_factory=ChunkMeta, description="Metadata dictionary for the chunk.")
    content: str = Field(..., description="The text content of the chunk.")
    content_offset: int = Field(default=0, description="Offset in original content for multi-part chunks.")
    content_length: int = Field(default=0, description="Length of this chunk from the offset")
    
    @model_serializer
    def serialize(self) -> Dict[str, Any]:
        return {
            "meta": self.meta_model_dump,
            "content": self.content,
        }
    
    @property
    def meta_model_dump(self) -> Dict[str, Any]:
        """Get the metadata as a dictionary, including content offset and length."""
        meta = self.meta.model_dump()
        meta["content_offset"] = self.content_offset
        meta["content_length"] = self.content_length
        return meta
        
    @property
    def json_envelope(self) -> str:
        """Get the JSON envelope / wrapping of this chunk as a string, ensuring accountability for _all_ tokens."""
        return self.to_str(clear={"content": "", "meta": {}})

    def to_str(self, clear: Dict[str, Any] | None = None) -> str:
        """Serialize chunk to JSON string.
        
        Args:
            clear: Dict of fields to _clear_ the values of, and what to replace them with.
                ex. {"content": "", "meta": {}} will ensure content is an empty string and meta is an empty dict.
        """
        data = self.model_dump()

        for key, value in (clear or {}).items():
            data[key] = value

        return json.dumps(data, ensure_ascii=False)
        
    def __str__(self) -> str: 
        return self.to_str()  # Alias: to_str()

    def to_encodable_chunk(self) -> EncodableChunk:
        """Convert to EncodableChunk for serialization."""
        from pgmcp.chunking.encodable_chunk import EncodableChunk
        return EncodableChunk.from_chunk(self)
