from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, Any, Dict

from pydantic import BaseModel, Field, model_serializer
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from pgmcp.chunking.chunk_meta import ChunkMeta
from pgmcp.chunking.heredoc_yaml import HeredocYAML


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
            "meta": self.meta.model_dump(),
            "content": self.content,
        }
    
        
    @property
    def yaml_envelope(self) -> str:
        """Get the YAML envelope / wrapping of this chunk as a string, ensuring accountability for _all_ tokens."""
        empty = {
            "meta": {},
            "content": "",
        }
        return HeredocYAML.dump(empty)

    def to_str(self) -> str:
        """Serialize chunk to YAML string."""
        return HeredocYAML.dump(self.model_dump())

    def __str__(self) -> str: 
        return self.to_str()  # Alias: to_str()

    def to_encodable_chunk(self) -> EncodableChunk:
        """Convert to EncodableChunk for serialization."""
        from pgmcp.chunking.encodable_chunk import EncodableChunk
        return EncodableChunk.from_chunk(self)
