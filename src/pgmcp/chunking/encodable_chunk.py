"""A chunk that has a specific tiktoken model and max_size set."""

from copy import deepcopy
from typing import Any, ClassVar, Dict

import tiktoken

from pydantic import Field, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
from typing_extensions import Self

from pgmcp.chunking.chunk import Chunk
from pgmcp.chunking.chunk_meta import ChunkMeta
from pgmcp.chunking.heredoc_yaml import HeredocYAML


class EncodableChunk(Chunk):
    """
    A chunk that has a specific tiktoken model and max_size set.
    """
    model_config = {
        "arbitrary_types_allowed": True
    }

    _encoders: ClassVar[Dict[str, Any]] = {}
    
    model: str = Field("cl100k_base", description="tiktoken model name for encoding.")
    max_tokens: int = Field(8191, description="Max tokens allowed for serialized chunk.")

    @property
    def encoder(self):
        if self.model not in self._encoders:
            self._encoders[self.model] = tiktoken.get_encoding(self.model)
        return self._encoders[self.model]

    @property
    def max_token_count(self) -> int:
        return self.max_tokens

    @property
    def is_overflowing(self) -> bool:
        return self.token_count > self.max_tokens

    @property
    def token_count(self) -> int:
        """Get the final form, authoritative token count of this object in its serialized YAML form."""
        return len(self.encoder.encode(self.to_str()))

    @property
    def content_max_token_count(self) -> int:
        """How many tokens are available for content (max_tokens - meta_token_count)"""
        return self.max_tokens - self.meta_token_count

    @property
    def content_token_count(self) -> int:
        """How many tokens are used by the content determined by subtracting it from token_count"""
        full_token_count = self.token_count
        original_content = self.content
        self.content = ""
        content_missing_token_count = self.token_count
        self.content = original_content
        return full_token_count - content_missing_token_count

    @property
    def meta_token_count(self) -> int:
        full_token_count = self.token_count
        original_meta = self.meta.model_dump()
        self.meta = ChunkMeta.model_validate({}) # empty meta
        meta_missing_token_count = self.token_count
        self.meta = ChunkMeta.model_validate(original_meta)
        return full_token_count - meta_missing_token_count

    # == Sub-Chunking Helpers ==================================================================
    
    def to_chunk(self) -> Chunk:
        """Convert to a base Chunk, stripping out model/max_tokens settings."""
        return Chunk(
            meta=deepcopy(self.meta),
            content=self.content,
            content_offset=self.content_offset,
            content_length=self.content_length
        )

    def spawn_sub_chunk(self, content: str | None = None, offset: int = 0) -> "EncodableChunk":
        """Create an empty sub-chunk with the same metadata and model/max_tokens settings."""
        content = content or ""
        return EncodableChunk(
            meta=deepcopy(self.meta),
            content=content or "",
            content_offset=offset,
            content_length=len(content),
            model=self.model,
            max_tokens=self.max_tokens
        )

    # == Constructors ============================================================================
    
    @classmethod
    def from_chunk(cls, chunk: Chunk, model: str = "cl100k_base", max_tokens: int = 8191) -> "EncodableChunk":
        return cls(
            meta=chunk.meta,
            content=chunk.content,
            content_offset=chunk.content_offset,
            content_length=chunk.content_length,
            model=model,
            max_tokens=max_tokens
        )


    @model_validator(mode="after")
    def check_impossible_state(self) -> Self:
        """
        Pydantic model validator: Ensures that the chunk is not constructed in an impossible state.

        This validator checks that if the content is empty and the effective content token budget is zero or less,
        the chunk is impossible: even empty content cannot fit. This prevents silent misconfiguration where meta are set so high that no content (not even empty) could ever fit.
        """
        if self.content == "" and self.content_max_token_count <= 0:
            raise ValueError(
                f"Impossible chunk: no room for any content (content_max_token_count={self.content_max_token_count}) with empty content. "
                f"Reduce meta or increase max_tokens."
            )
        return self
