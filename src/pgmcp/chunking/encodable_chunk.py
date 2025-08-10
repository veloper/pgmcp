"""A chunk that has a specific tiktoken model and max_size set."""

from copy import deepcopy
from typing import Any, ClassVar, Dict

import tiktoken

from pydantic import Field, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
from typing_extensions import Self

from pgmcp.chunking.chunk import Chunk
from pgmcp.chunking.heredoc_yaml import HeredocYAML


class EncodableChunk(Chunk):
    """
    A chunk that has a specific tiktoken model and max_size set.

    Manages calculations of three pools of tokens budgets:

        1. Max Tokens: How big the _entire serialized_ chunk is allowed to be.
        2. Overhead tokens: Metadata + YAML envelope + Reserve tokens
        3. Effective Max Tokens: How many tokens are left for content after accounting for overhead
        
    See:
    
        +---------- Overhead Tokens ----------+
        |                                     |          
        [---Metadata---][------ Reserve ------][------------------Content------------------]
        |                                      |                                           |
        |                                      +---------- Effective Max Tokens -----------+
        |                                                                                  |                                           
        +---------------------------------Max Tokens---------------------------------------+
    """
    model_config = {
        "arbitrary_types_allowed": True
    }

    _encoders: ClassVar[Dict[str, Any]] = {}
    
    model: str = Field("cl100k_base", description="tiktoken model name for encoding.")
    max_tokens: int = Field(8191, description="Max tokens allowed for serialized chunk.")
    reserve_tokens: int = Field(0, description="Number of tokens reserved for any reason, eating content budget.")

    @property
    def encoder(self):
        if self.model not in self._encoders:
            self._encoders[self.model] = tiktoken.get_encoding(self.model)
        return self._encoders[self.model]

    @classmethod
    def _get_encoder(cls):
        # Use default model for static envelope token count
        if "cl100k_base" not in cls._encoders:
            cls._encoders["cl100k_base"] = tiktoken.get_encoding("cl100k_base")
        return cls._encoders["cl100k_base"]

    # == Hard counts =============================================================================

    @property
    def content_token_count(self) -> int:
        """Get the token count of the raw content string (no escaping, no serialization)."""
        return len(self.encoder.encode(self.content))

    @property
    def meta_token_count(self) -> int:
        """Get the token count of the YAML-serialized meta mapping (no envelope). 
        This means in yaml:
        
        ```yaml
        meta:
          key1: value1
          key2: value2
        ```
        
        this is getting lines 2 and 3, not the key "meta" itself.
        """
        meta_yaml = HeredocYAML.dump(self.meta.model_dump())
        return len(self.encoder.encode(meta_yaml))

    @property
    def envelope_token_count(self) -> int:
        """Get the token count of the static YAML envelope structure (keys, colons, newlines, indentation, etc.), excluding meta and content values.
        ```yaml
        meta:
          key1: value1
          key2: value2
        content: |-
          This is the content of the chunk.
        ```

        This would only get `meta:` and `content: |-`
        """
        return len(self.encoder.encode(HeredocYAML.dump({"meta": {}, "content": " "})))

    @property
    def reserve_token_count(self) -> int:
        return self.reserve_tokens

    @property
    def max_token_count(self) -> int:
        return self.max_tokens

    # == Derived counts ======================================================================

    @property
    def overhead_token_count(self) -> int:
        """Get the token count of Meta Data + YAML envelope + Reserve tokens."""
        return self.meta_token_count + self.envelope_token_count + self.reserve_token_count

    @property
    def content_max_token_count(self) -> int:
        """Get the effective max tokens count representing the total space the content can occupy."""
        return max(0, self.max_tokens - self.overhead_token_count)

    @property
    def content_remaining_token_count(self) -> int:
        """Get the remaining tokens available for the content to grow into."""
        return max(0, self.content_max_token_count - self.content_token_count)

    @property
    def is_overflowing(self) -> bool:
        """
        Check if the chunk's total token count (meta + envelope + reserve + content) exceeds the max tokens allowed.
        This ensures that reserve tokens are always respected as a hard budget subtraction, regardless of YAML serialization quirks.
        """
        return (self.overhead_token_count + self.content_token_count) > self.max_tokens

    @property
    def token_count(self) -> int:
        """Get the final form, authoritative token count of this object in its serialized YAML form."""
        return len(self.encoder.encode(self.to_str()))

    
    # == Sub-Chunking Helpers ==================================================================
    
    def to_chunk(self) -> Chunk:
        """Convert to a base Chunk, stripping out model/max_tokens/reserve settings."""
        return Chunk(
            meta=deepcopy(self.meta),
            content=self.content,
            content_offset=self.content_offset,
            content_length=self.content_length
        )

    def spawn_sub_chunk(self, content: str | None = None, offset: int = 0) -> "EncodableChunk":
        """Create an empty sub-chunk with the same metadata and model/max_tokens/reserve settings."""
        content = content or ""
        return EncodableChunk(
            meta=deepcopy(self.meta),
            content=content or "",
            content_offset=offset,
            content_length=len(content),
            model=self.model,
            max_tokens=self.max_tokens,
            reserve_tokens=self.reserve_tokens
        )

    # == Constructors ============================================================================
    
    @classmethod
    def from_chunk(cls, chunk: Chunk, model: str = "cl100k_base", max_tokens: int = 8191, reserve_tokens: int = 0) -> "EncodableChunk":
        return cls(
            meta=chunk.meta,
            content=chunk.content,
            content_offset=chunk.content_offset,
            content_length=chunk.content_length,
            model=model,
            max_tokens=max_tokens,
            reserve_tokens=reserve_tokens
        )


    @model_validator(mode="after")
    def check_impossible_state(self) -> Self:
        """
        Pydantic model validator: Ensures that the chunk is not constructed in an impossible state.

        This validator checks that if the content is empty and the effective content token budget is zero or less,
        the chunk is impossible: even empty content cannot fit. This prevents silent misconfiguration where reserve
        tokens or meta are set so high that no content (not even empty) could ever fit.
        """
        if self.content == "" and self.content_max_token_count <= 0:
            raise ValueError(
                f"Impossible chunk: no room for any content (content_max_token_count={self.content_max_token_count}) with empty content. "
                f"Reduce meta or reserve_tokens, or increase max_tokens."
            )
        return self
